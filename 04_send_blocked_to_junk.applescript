use framework "Foundation"
use scripting additions

set projectFolder to "__PROJECT_DIR__"
set outputFolder to "__PROJECT_DIR__/output"
set blockedCsv to projectFolder & "/expediteurs_bloques.csv"
set ruleName to "Nettoyage Mail - Expéditeurs bloqués vers Indésirable"

set blockedAddresses to my readAddressesFromCsv(blockedCsv)
set reportLines to {"adresse;action;details"}

using terms from application "Mail"
	with timeout of 3600 seconds
		tell application "Mail"
			set targetMailbox to my junkMailbox()
			if targetMailbox is missing value then error "Aucune boite Indésirable/Junk/Spam n'a ete trouvee dans Mail."
			
			set targetRule to my findRuleByName(ruleName)
			if targetRule is missing value then
				set targetRule to make new rule at end of rules with properties {name:ruleName, enabled:true}
			end if
			
			tell targetRule
				set enabled to false
				set all conditions must be met to false
				set should move message to true
				set move message to targetMailbox
				set stop evaluating rules to true
				delete every rule condition
			end tell
			
			repeat with senderAddress in blockedAddresses
				set normalizedAddress to senderAddress as text
				if normalizedAddress is not "" then
					tell targetRule
						make new rule condition at end of rule conditions with properties {rule type:from header, qualifier:equal to value, expression:normalizedAddress}
					end tell
					set end of reportLines to my csvEscape(normalizedAddress) & ";regle_ajoutee;" & my csvEscape(ruleName)
				end if
			end repeat
			
			set enabled of targetRule to true
		end tell
	end timeout
end using terms from

set AppleScript's text item delimiters to linefeed
set reportOutput to reportLines as text
set AppleScript's text item delimiters to ""

set outputPath to outputFolder & "/rapport_regle_spam.csv"
my ensureFolderExists(outputFolder)
my writeTextFile(outputPath, reportOutput)
return outputPath

on findRuleByName(targetName)
	using terms from application "Mail"
		tell application "Mail"
			repeat with existingRule in rules
				try
					if (name of existingRule as text) is targetName then return existingRule
				end try
			end repeat
		end tell
	end using terms from
	return missing value
end findRuleByName

on junkMailbox()
	set preferredNames to {"indésirable", "indesirable", "junk", "spam", "courrier indésirable", "courrier indesirable"}
	
	using terms from application "Mail"
		tell application "Mail"
			repeat with candidateMailbox in every mailbox
				try
					set mailboxName to my normalizeMailboxName(name of candidateMailbox as text)
					if preferredNames contains mailboxName then return candidateMailbox
				end try
			end repeat
		end tell
	end using terms from
	
	return missing value
end junkMailbox

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
				if senderAddress is not "" and senderAddress is not in knownAddresses then set end of knownAddresses to senderAddress
			end if
		end if
	end repeat
	return knownAddresses
end readAddressesFromCsv

on normalizeEmailAddress(addressText)
	set addressText to my trimText(addressText)
	if addressText begins with "\"" and addressText ends with "\"" then
		if (count of characters of addressText) is greater than 1 then set addressText to text 2 thru -2 of addressText
	end if
	set nsAddress to current application's NSString's stringWithString:addressText
	return (nsAddress's lowercaseString() as text)
end normalizeEmailAddress

on normalizeMailboxName(nameText)
	set nsName to current application's NSString's stringWithString:(my trimText(nameText))
	return (nsName's lowercaseString() as text)
end normalizeMailboxName

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
