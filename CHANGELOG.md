# 📑 Change Log

## v0.4.1-beta

12.05.2024

### What's Changed
- Added new types of logs:
  - Actions with deleted messages: All deleted messages are now recorded, providing transparency regarding deleted data.
  - Edited messages: You can now view the history of changes to messages, which helps to control the integrity of communication.
  - Penalties applied for violations: A system of penalties for violations of the rules has been introduced, ensuring order and fairness in the system.
  - Transactions or changes in the economy: Added the ability to track all financial transactions and changes in the economy of the system.
  - Considered proposals and ideas: Now all proposed ideas and proposals are being recorded, which contributes to the development of the idea and improvement of the system.

- The following changes have been made to the functionality:
  - Reaction roles: Added the ability to assign roles to users based on their reactions, which increases participation in the community.
  - Reaction Commands: Users can now use reaction commands to perform certain actions, improving interaction.
  - Work in the economy: A new economic system has been introduced that allows users to carry out various financial transactions.
  - Games in economics: Added the ability to play various games using the game currency from the system's economy.
  - New settings: Users have access to new settings that allow them to manage various aspects of the system.
  - Theft: A theft feature has been introduced that allows users to interact with the economic system through theft.
  - New database system: The database system has been updated to provide more efficient and reliable data storage.


## v0.3.1-beta

14.04.2024

### What's Changed
1. Added settings for the server store
2. Fixed music playback
3. Added localization for the `/delete-category` command
4. The execution time for deleting channels in `/delete-category` has been accelerated
5. New logic for buying roles
6. New time entry system
7. Added distribution settings
8. A new kind of invites team
9. Added 3 new leaderboards time in voice, points and number of messages 
10. The avatar command has been added
11. Added special features in ideas
 - Ban
 - Mute
 - Image ban
 - Auto-delete branches upon approval/refusal
 - Own delay on ideas
12. Added score, voice time and messages
13. Added a polling system, the command `/poll` and `Finish poll`
14. Added a server item store
15. Added an error handler **interaction failed**, instead of it there will be a suggestion to repeat the action
16. Added tracking of invitations and the `/invites' command
17. Added translation for arguments in the `/help` command
18. Fixed approval/rejecting an idea in the ideas module
19. Added emoji verification


## Alpha/v0.2.2

09.03.2024

### What's Changed
1. The `tempban` and `/deletecategory` commands have been added, as well as the functionality of linking an image to a welcome message. 
2. The selector has been fixed, now all roles and channels are available. 
3. The appearance of the `help` and `ping` commands has been changed. 
4. The speed of command execution has decreased, as has the rate of database queries. 
5. A new argument management system has been implemented. 
6. The default color of system messages has now been updated to make them effectively invisible. 
7. The ability to alter the charge type without re-entering data on replicas and delays has been added, and the time display has been corrected (previously only English was shown).


## Alpha/v0.2.1

17.02.2024

### What's Changed
1. Added the leaderboard command.
2. Updated economy settings.
3. Added the ability to add custom emojis for the economy.
4. Now the server is automatically added to the database, and also deleted from the database if the bot was kicked out of the server and was not added back within 1 day.
5. There is a limit on the commands `gift`, `take` now the maximum amount can be 1 million.
6. The help command has been updated, new services present in the update have been added.
7. Fixed the perception of commands for further rights verification.
8. New command execution rules have been added: cooldown, allowed roles, allowed channels. 
9. A new temporary roles service has been added.
10. Database acquisition time is accelerated.
11. The idea service has been added.
12. The return of the music service in a new form.
13. The settings of the greeting service have been disclosed and are now in the general me.
14. The translation function has been updated.

### Languages added
* Indonesia 🇮🇩
* Danish 🇩🇰
* German 🇩🇪
* Spanish 🇪🇸
* French 🇫🇷
* Polish 🇵🇱
* Turkish 🇹🇷


## Alpha/v0.1.2

09.12.2023

### What's Changed

* **`/activity`** - Fixed the work of the team
* Updated emojis in economy and settings
* The music module has been completely removed
* Added the command `/clone role`&#x20;
* Changed the type of auto-reaction settings
* Changing the appearance of the `l.help` command
* Added the welcome module:&#x20;
  * Automatic roles
  * Automatic greeting for newbies
* Added a translation to the message when the bot is mentioned
* Reduced command processing time

## Release - Alpha/v0.1.1

26.11.2023

### Main functions:

* **Moderation**: The ability to send messages on behalf of the bot and clean up the chat from messages.
* **Music**: The ability to listen to music, the presence of temporary pause and full mute functions, as well as the ability to adjust the volume - all these are provided as functions available for use.
* **Translator**: When selecting a message, all languages available in the discord are provided. After selecting one of them, the translation into the selected language takes place.
* **Activity**: To create an activity in a channel, you must first select the desired channel, and then the activity itself. The bot displays the available activities and displays their name, as well as the maximum number of participants.
* **Settings**: You can change the prefix, language, disable commands, change the color of system messages, as well as set automatic messages in branches and forums, and set automatic reactions.
* **Embed-buidler**: The ability to send embed messages without using a webhook.
* **Available languages:**
  * English(English)
  * Russian(Русский)