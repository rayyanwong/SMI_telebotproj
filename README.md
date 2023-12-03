# SMI_telebotproj

First telegram bot project - done within 72 hours for my National Service SCS Recon Camp.

Project uses LocalDB - SQLite to store data of "regulars" in the camp

Cadets log their attendance by Booking in. 
  - Booking in allows their attendance to be marked for the whole week
  - If they are unable to book into camp, they will be able to indicate how long they will be gone for and the reason for not being in camp
  - This is then reflected in the PARADE STATE
  - Upon booking in, telebot uses Geolocation to confirm that their location is within camp before marking them as present.

Daily attendance is then logged onto an excel file and DB, which can be used to generate a parade state.

Parade state - Statuses of everyone in camp. Strength of the camp and reasons for not being in camp. ( Used for attendance taking ) 

Excel sheet can show attendance of each person in camp throughout 3 months - can be copied and pasted into google sheets which is used by the superiors to track individual soldier's performance.

### PROJECT IS NO LONGER MAINTAINED
