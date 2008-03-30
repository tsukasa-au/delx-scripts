/* Copyright 2008 James Bunton <jamesbunton@fastmail.fm>
 * Licensed for distribution under the GPL version 2.
 *
 * Dump the contents of the OSX address book in a format usable as by Mutt as
 * an alias file.
 */


#import <Foundation/Foundation.h>
#import <AddressBook/AddressBook.h>

#define NSPrint(fmt, ...) [[NSString stringWithFormat:fmt, ## __VA_ARGS__] writeToFile:@"/dev/stdout" atomically:NO encoding:NSUTF8StringEncoding error:nil]

int
main()
{
	NSAutoreleasePool* pool = [[NSAutoreleasePool alloc] init];

	for(ABPerson* person in [[ABAddressBook sharedAddressBook] people]) {
		NSString* firstName = [[person valueForProperty:kABFirstNameProperty] description];
		NSString* lastName = [[person valueForProperty:kABLastNameProperty] description];
		NSString* nickName = [[person valueForProperty:kABNicknameProperty] description];

		if(!([firstName length] > 0 && [lastName length] > 0)) {
			continue; // Ignore empty entries
		}

		// Mutt requires a key
		if([nickName length] > 0) {
			NSPrint(@"alias %@ ", nickName);
		} else {
			NSPrint(@"alias %@%@ ", firstName, lastName);
		}

		NSPrint(@"%@ %@ ", firstName, lastName);

		// WTF does ABMultiValue exist for? No fast enumeration? What's wrong with NSArray?!
		ABMultiValue* emails = [person valueForProperty:kABEmailProperty];
		for(unsigned int i = 0; i < [emails count]; ++i) {
			NSPrint(@"%@ ", [emails valueAtIndex:i]);
		}
		NSPrint(@"\n");
	}

	[pool release];

	return 0;
}

