use framework "Foundation"
use scripting additions

set periodYear to 2026
set periodMonthNumber to 7
set projectFolder to "__PROJECT_DIR__"
set outputFolder to "__PROJECT_DIR__/output"
set protectedCsv to projectFolder & "/expediteurs_proteges.csv"
set blockedCsv to projectFolder & "/expediteurs_bloques.csv"
set cleanupOnlyCsv to projectFolder & "/expediteurs_nettoyer_sans_bloquer.csv"
set startDate to my buildDate(periodYear, periodMonthNumber, 1)
set endDate to my firstDayOfNextMonth(periodYear, periodMonthNumber)

set protectedAddresses to my readAddressesFromCsv(protectedCsv)
set blockedAddresses to my readAddressesFromCsv(blockedCsv)
set cleanupOnlyAddresses to my readAddressesFromCsv(cleanupOnlyCsv)
set groupedRows to my groupedSendersForPeriod(startDate, endDate)

set pendingLines to {"nom;adresse;nombre_de_mails;statut;action_recommandee"}
repeat with rowData in groupedRows
	set senderName to item 1 of rowData
	set senderAddress to item 2 of rowData
	set senderCount to item 3 of rowData
	
	set senderStatus to "inconnu"
	set recommendedAction to "revoir"
	
	if protectedAddresses contains senderAddress then
		set senderStatus to "protege"
		set recommendedAction to "conserver"
	else if blockedAddresses contains senderAddress then
		set senderStatus to "bloque"
		set recommendedAction to "nettoyer"
	else if cleanupOnlyAddresses contains senderAddress then
		set senderStatus to "nettoyer_sans_bloquer"
		set recommendedAction to "nettoyer"
	end if
	
	set csvLine to my csvEscape(senderName) & ";" & my csvEscape(senderAddress) & ";" & senderCount & ";" & senderStatus & ";" & recommendedAction
	if senderStatus is "inconnu" then set end of pendingLines to csvLine
end repeat

set AppleScript's text item delimiters to linefeed
set pendingOutput to pendingLines as text
set AppleScript's text item delimiters to ""

set pendingOutputPath to outputFolder & "/expediteurs_a_traiter.csv"
my ensureFolderExists(outputFolder)
my writeTextFile(pendingOutputPath, pendingOutput)
return pendingOutputPath

on readAddressesFromCsv(filePath)
	if my fileExists(filePath) is false then return {}
	set csvText to my readTextFile(filePath)
	set csvLines to paragraphs of csvText
	set knownAddresses to {}
	
	repeat with lineIndex from 2 to count of csvLines
		set currentLine to my trimText(item lineIndex of csvLines)
		if currentLine is not "" then
			set fields to my splitText(currentLine, ";")
			if (count of fields) is greater than or equal to 2 then
				set senderAddress to my normalizeEmailAddress(item 2 of fields)
				set end of knownAddresses to senderAddress
			end if
		end if
	end repeat
	return knownAddresses
end readAddressesFromCsv

on groupedSendersForPeriod(startDate, endDate)
	set senderAddresses to {}
	set senderNames to {}
	set senderCounts to {}
	
	using terms from application "Mail"
		with timeout of 3600 seconds
			tell application "Mail"
				set targetMessages to (messages of inbox whose date received is greater than or equal to startDate and date received is less than endDate)
				
				repeat with msg in targetMessages
					try
						set rawSender to sender of msg as text
						set senderAddress to my normalizeEmailAddress(my senderAddressFromHeader(rawSender))
						set senderName to my senderNameFromHeader(rawSender)
						set existingIndex to my indexOfItem(senderAddress, senderAddresses)
						
						if existingIndex is 0 then
							set end of senderAddresses to senderAddress
							set end of senderNames to senderName
							set end of senderCounts to 1
						else
							set item existingIndex of senderCounts to (item existingIndex of senderCounts) + 1
						end if
					end try
				end repeat
			end tell
		end timeout
	end using terms from
	
	set groupedRows to {}
	repeat with i from 1 to count of senderAddresses
		set end of groupedRows to {item i of senderNames, item i of senderAddresses, item i of senderCounts}
	end repeat
	return groupedRows
end groupedSendersForPeriod

on senderAddressFromHeader(rawSender)
	set rawSender to my trimText(rawSender)
	if rawSender contains "<" and rawSender contains ">" then
		set leftParts to my splitText(rawSender, "<")
		set rightPart to item -1 of leftParts
		set rightParts to my splitText(rightPart, ">")
		return my trimText(item 1 of rightParts)
	end if
	return rawSender
end senderAddressFromHeader

on senderNameFromHeader(rawSender)
	set rawSender to my trimText(rawSender)
	if rawSender contains "<" then
		set leftParts to my splitText(rawSender, "<")
		set senderName to my trimText(item 1 of leftParts)
		if senderName begins with "\"" and senderName ends with "\"" then
			if (count of characters of senderName) is greater than 1 then set senderName to text 2 thru -2 of senderName
		end if
		return senderName
	end if
	return ""
end senderNameFromHeader

on normalizeEmailAddress(addressText)
	set addressText to my trimText(addressText)
	if addressText begins with "\"" and addressText ends with "\"" then
		if (count of characters of addressText) is greater than 1 then set addressText to text 2 thru -2 of addressText
	end if
	set nsAddress to current application's NSString's stringWithString:addressText
	return (nsAddress's lowercaseString() as text)
end normalizeEmailAddress

on writeTextFile(filePath, fileContents)
	set NSString to current application's NSString's stringWithString:fileContents
	set didWrite to NSString's writeToFile:filePath atomically:true encoding:(current application's NSUTF8StringEncoding) |error|:(missing value)
	if (didWrite as boolean) is false then error "Impossible d'ecrire le fichier : " & filePath
end writeTextFile

on readTextFile(filePath)
	set NSString to current application's NSString's stringWithContentsOfFile:filePath encoding:(current application's NSUTF8StringEncoding) |error|:(missing value)
	if NSString is missing value then error "Impossible de lire le fichier : " & filePath
	return NSString as text
end readTextFile

on fileExists(filePath)
	set fileManager to current application's NSFileManager's defaultManager()
	return (fileManager's fileExistsAtPath:filePath) as boolean
end fileExists

on ensureFolderExists(folderPath)
	set fileManager to current application's NSFileManager's defaultManager()
	fileManager's createDirectoryAtPath:folderPath withIntermediateDirectories:true attributes:(missing value) |error|:(missing value)
end ensureFolderExists

on buildDate(theYear, theMonthNumber, theDay)
	set comps to current application's NSDateComponents's alloc()'s init()
	comps's setYear:theYear
	comps's setMonth:theMonthNumber
	comps's setDay:theDay
	comps's setHour:0
	comps's setMinute:0
	comps's setSecond:0
	set cal to current application's NSCalendar's currentCalendar()
	return (cal's dateFromComponents:comps) as date
end buildDate

on firstDayOfNextMonth(theYear, theMonthNumber)
	if theMonthNumber is 12 then
		return my buildDate(theYear + 1, 1, 1)
	else
		return my buildDate(theYear, theMonthNumber + 1, 1)
	end if
end firstDayOfNextMonth

on monthLabelFromNumber(theMonthNumber)
	set monthNames to {"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}
	return item theMonthNumber of monthNames
end monthLabelFromNumber

on csvEscape(t)
	set t to t as text
	set AppleScript's text item delimiters to "\""
	set parts to text items of t
	set AppleScript's text item delimiters to "\"\""
	set escapedText to parts as text
	set AppleScript's text item delimiters to ""
	return "\"" & escapedText & "\""
end csvEscape

on splitText(sourceText, delimiterText)
	set AppleScript's text item delimiters to delimiterText
	set parts to text items of (sourceText as text)
	set AppleScript's text item delimiters to ""
	return parts
end splitText

on trimText(sourceText)
	set sourceText to sourceText as text
	repeat while sourceText begins with space or sourceText begins with tab or sourceText begins with return or sourceText begins with linefeed
		if sourceText is "" then exit repeat
		set sourceText to text 2 thru -1 of sourceText
	end repeat
	repeat while sourceText ends with space or sourceText ends with tab or sourceText ends with return or sourceText ends with linefeed
		if sourceText is "" then exit repeat
		set sourceText to text 1 thru -2 of sourceText
	end repeat
	return sourceText
end trimText

on indexOfItem(theItem, theList)
	repeat with i from 1 to count of theList
		if item i of theList is theItem then return i
	end repeat
	return 0
end indexOfItem
