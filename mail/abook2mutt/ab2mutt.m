/* Copyright 2008 James Bunton <jamesbunton@fastmail.fm>
 * Licensed for distribution under the GPL version 2.
 *
 * Dump the contents of the OSX address book as a Mutt alias file
 */


#import <Foundation/Foundation.h>
#import <AddressBook/AddressBook.h>


void
NSPrint(NSString* format, ...)
{
	va_list args;
	va_start(args, format);
	NSString* string = [[NSString alloc] initWithFormat:format arguments:args];
	va_end(args);
	[string writeToFile:@"/dev/stdout" atomically:NO encoding:NSUTF8StringEncoding error:nil];
	[string release];
}


@interface NSString (james)
-(NSString*) keepOnlyCharacterSet:(NSCharacterSet*)keepChars;
@end
@implementation NSString (james)
-(NSString*)
keepOnlyCharacterSet:(NSCharacterSet*)keepChars;
{
	NSMutableString* ret = [[NSMutableString alloc] init];
	NSScanner* scanner = [NSScanner scannerWithString:self];
	NSString* temp;
	while(![scanner isAtEnd]) {
		if([scanner scanCharactersFromSet:keepChars intoString:&temp]) {
			[ret appendString:temp];
		} else {
			[scanner setScanLocation:1+[scanner scanLocation]];
		}
	}
	return [ret autorelease];
}
@end


void
printMuttAlias(NSString* key, NSString* firstName, NSString* lastName, ABMultiValue* emails)
{
	key = [[key lowercaseString] keepOnlyCharacterSet:[NSCharacterSet lowercaseLetterCharacterSet]];

	for(unsigned int i = 0; i < [emails count]; ++i) {
		NSString* keySuffix = @"";
		if(i > 0) {
			keySuffix = [NSString stringWithFormat:@"%d", i];
		}
		NSPrint(@"alias %@%@ \"%@ %@\" <%@>\n", key, keySuffix, firstName, lastName, [emails valueAtIndex:i]);
	}
}

int
main()
{
	NSAutoreleasePool* pool = [[NSAutoreleasePool alloc] init];

	for(ABPerson* person in [[ABAddressBook sharedAddressBook] people]) {
		NSString* firstName = [[person valueForProperty:kABFirstNameProperty] description];
		NSString* lastName = [[person valueForProperty:kABLastNameProperty] description];
		NSString* nickName = [[person valueForProperty:kABNicknameProperty] description];
		// WTF does ABMultiValue exist for? No fast enumeration? What's wrong with NSArray?!
		ABMultiValue* emails = [person valueForProperty:kABEmailProperty];

		if([emails count] == 0) {
			continue;
		}

		// Generate an entry for Nick and FirstLast
		if([nickName length] > 0) {
			printMuttAlias(nickName, firstName, lastName, emails);
		}
		if([firstName length] > 0 && [lastName length] > 0) {
			NSString* key = [NSString stringWithFormat:@"%@%@", firstName, lastName];
			printMuttAlias(key, firstName, lastName, emails);
		}
	}

	[pool release];

	return 0;
}

