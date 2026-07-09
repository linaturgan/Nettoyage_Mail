use framework "Foundation"
use scripting additions

set periodYear to 2026
set periodMonthNumber to 7
set outputFolder to "__PROJECT_DIR__/output"
set startDate to my buildDate(periodYear, periodMonthNumber, 1)
set endDate to my firstDayOfNextMonth(periodYear, periodMonthNumber)

set groupedRows to my groupedSendersForPeriod(startDate, endDate)

set csvLines to {"nom;adresse;nombre_de_mails"}
repeat with rowData in groupedRows
	set senderName to item 1 of rowData
	set senderAddress to item 2 of rowData
	set senderCount to item 3 of rowData
	set csvLine to my csvEscape(senderName) & ";" & my csvEscape(senderAddress) & ";" & senderCount
	set end of csvLines to csvLine
end repeat

set AppleScript's text item delimiters to linefeed
set csvOutput to csvLines as text
set AppleScript's text item delimiters to ""

set monthLabel to my monthLabelFromNumber(periodMonthNumber)
set outputPath to outputFolder & "/expediteurs_" & periodYear & "_" & monthLabel & ".csv"
my ensureFolderExists(outputFolder)
my writeTextFile(outputPath, csvOutput)
return outputPath

on groupedSendersForPeriod(startDate, endDate)
	set senderAddresses to {}
	set senderNames to {}
	set senderCounts to {}
	
	using terms from application "Mail"
		tell application "Mail"
			set targetMessages to messages of inbox
			
			repeat with msg in targetMessages
				try
					set receivedAt to date received of msg
					if receivedAt is greater than or equal to startDate and receivedAt is less than endDate then
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
					end if
				end try
			end repeat
		end tell
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
	set nsString to current application's NSString's stringWithString:fileContents
	set didWrite to nsString's writeToFile:filePath atomically:true encoding:(current application's NSUTF8StringEncoding) |error|:(missing value)
	if (didWrite as boolean) is false then error "Impossible d'ecrire le fichier : " & filePath
end writeTextFile

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
