#imports and initialisation
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
import logging
from typing import Final
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import sqlite3
from datetime import datetime,timedelta,date
import pandas as pd
import csv

TOKEN : Final = "6178172385:AAEEbHfVWUObNOYge7gdpd413Mqxn-hhRQU"
BOT_USERNAME: Final = "@rayyantest3bot"
DATE_REGEX: Final = r"^(?:(?:31(\/|-|\.)(?:0?[13578]|1[02]))\1|(?:(?:29|30)(\/|-|\.)(?:0?[13-9]|1[0-2])\2))(?:(?:1[6-9]|[2-9]\d)?\d{2})$|^(?:29(\/|-|\.)0?2\3(?:(?:(?:1[6-9]|[2-9]\d)?(?:0[48]|[2468][048]|[13579][26])|(?:(?:16|[2468][048]|[3579][26])00))))$|^(?:0?[1-9]|1\d|2[0-8])(\/|-|\.)(?:(?:0?[1-9])|(?:1[0-2]))\4(?:(?:1[6-9]|[2-9]\d)?\d{2})$"
FD_NO, NAME, MASKED_IC,REG_COMPLETE, LOCATION, INFOTOEDIT, EDITNAME, STATUSBO, NOTBOCHECK, NOTBOREASON, NOTBOREASON2, NOTBOREASON3,GETSTATUSSTART, EDITSTATUS, CHECKVALIDSTATUS, UPDATEOOC2, UPDATEOOC3, UPDATEOOC4, TEMPSTATUS2, TEMPSTATUS3, TEMPSTATUS4 = range(21)

camp_bounds: Final = {'Pasir Laba': [[1.33080,1.3374],[103.66808,103.67703]]}
COURSE_NAME: Final = '10/23 AISCC'
NUM_PLATOONS: Final = 2
DB_NAME: Final = "SMI.db"

#----------------------create database--------------------------

# do note that SMI.db can be changed to any other name of database, in hindsight.. probably sld have made a variable for that such that other references would change in the codes below... mybadLOL low level developer moments [FIXED]

# con = sqlite3.connect(DB_NAME)
# con.execute("CREATE TABLE Cadets( fd_no INT primary key not null, name text not null, masked_ic text not null)")
# con.execute("CREATE TABLE Perm_staff( full_name text primary key not null, rank text not null)")
# con.execute("CREATE TABLE cadet_leave( user_id int not null, start_date text not null, end_date text not null, primary key(user_id,start_date), foreign key (user_id) references registered_ids(user_id))")
# con.execute("CREATE TABLE cadet_status( user_id int not null, start_date text not null, end_date text not null, primary key (user_id,start_date), foreign key (user_id) references registered_ids(user_id))")
# con.execute('CREATE TABLE registered_ids( user_id text primary key not null, fd_no int not null, foreign key (fd_no) references Cadets(fd_no) )')
# con.execute('CREATE TABLE temp_status( user_id int not null, status text not null, start_date text not null, end_date text not null, primary key(user_id,status,start_date), foreign key(user_id) references registered_ids(user_id))')
# con.commit()
# con.close()


#------------------------- Notes of rayyan ---------------------------------

    #code is not fullproof yet, example, for excel updating of MC/Leave to make attendance to 0, if cadets try to play with it and put mc until next year,
    # this will cause excel df to be fragmented.. 
    # -> solution not being implemented yet due to lack of time, can look at possible solutions on stackoverflow (?)

    #might have an error where if end date is next week (for mc/leave) but excel will update attendance next week too after mc ends, ie
    # start 13-06-2023, ends 20-06-2023, code might update 1 for the rest of the week (of the end date) -> to fix it, look at updateMC() [FIXED]

    #have yet to implement ability to generate button for each avail status/mc/leave for cadets to edit due to lack of time
    # -> to do so, get req status/mc/leave results from db, make a button for each, then put as reply_keyboard for replykeyboardmarkup
    # -> note that to identify end date of status//mc/leave, it is using a composite key of start and user_id, could not think of a better unique 
    # identifier for it... but then again, if we could just generate a button for each status they would like to edit, this would not be a problem 
    # ->-> would be a good idea to implement buttons for each status rather for them to try and remember when their status even started
    # i would do that but i dont have the time XD

    #still might have better ways for filters.Regex statements to further fullproof inputs

    #additionally, it would be good if we could allow them to change their start dates of their status/leave/mc -> possible to do so but no time :,)

    #do note when changing of courses, make sure there is a new excel/ put in relevant dates into the excel workbook (make sure it is from Mon-Sun in 7s)
    #when changing courses too, go to COURSE_NAME to change it so that it reflects correct course when generating the pstate, number of platoons too..

    #yet to add conditional check if they have already registered before they use other functions >> i guess commanders sld let them all know to register first
    #before using it

    #important to restart bot if any error occurs, since i have not been able to think of a good way to handle errors such as NetworkError and more... 
    # then again,,, restarting the code shld fix most of the time...

    #if you are wondering why there are so many datetime codes being repeated, it was because i forgot about date comparison in sqlite3 and initially stored
    # as dd-mm-yyyy, hence '14-06-2023' is always greater than '13-07-2023', giving an error -> thus had to change to format yyyy-mm-dd

    #very new to pandas so if anyone is going to further work on this code [TLDR]
    # 1. Fix possibility of fragmented dataframe using pandas for excel sheet
    # 2. Generate buttons for each status and allow them to choose which to select
    # 3. Add a way for them to edit startdate too, not just enddate
    # 4. Consider better regex statements
    # 5. There ARE alot of repetitive functions/code in this, mainly is to make it simple for me to understand because this is my first telebot, and it was
    #    too late into this development where i discovered about user_data "states" , where i could do conditionals to see what state ( basically what they want to do )
    #    and provide the necessary services when applicable... 
    # 6. Consider using nosql instead, since data formats can be mutable and can put different ppl into diff collections based on their platoons, perhaps
    #    it would be much easier to handle to bunch of statuses people have...although i havent given much thought into it.
    # 7. Add error handlers for every possible problems this bot can run into, have yet to do that... fr need to study more into the module
    # 8. If you would really want, add logging, but I chose not to so that i dont flood my terminal, but logging is good to have.


#------------------------helpers------------------------------------------
def notinDB(person_id):
    con = sqlite3.connect(DB_NAME)
    result = con.execute("select fd_no from registered_ids where user_id = (?)",(person_id,)).fetchall()
    con.close()
    if len(result) == 0:
        return True
    return False

def getusername(person_id): # using person_id
    con = sqlite3.connect(DB_NAME)
    result = con.execute("select Cadets.name from Cadets inner join registered_ids on Cadets.fd_no = registered_ids.fd_no where registered_ids.user_id = (?)",(person_id,)).fetchone()
    con.close()
    return result[0]

def getusername2(fd_no): #using cadet 4D number
    con = sqlite3.connect(DB_NAME)
    result = con.execute("select Cadets.name from Cadets where Cadets.fd_no = (?)",(fd_no,)).fetchone()
    con.close()
    if result:
        return result[0]
    return None

def checkoncourse(fd_no):
    con = sqlite3.connect(DB_NAME)
    result = con.execute("select on_course from Cadets where fd_no =(?)",(fd_no,)).fetchone()
    con.close()
    if result:
        return result[0]
    return None

def checkstatus(person_id,start_date,db):
    con = sqlite3.connect(DB_NAME)
    statement = f'select end_date from {db} where user_id = (?) and start_date = (?)'
    result = con.execute(statement,(person_id,start_date)).fetchone()
    print(f'End date is {result}')
    if result:
        return True #got status
    return False 

def getenddate(person_id,start_date,db):
    con = sqlite3.connect(DB_NAME)
    statement = f'select end_date from {db} where user_id = (?) and start_date = (?)'
    result = con.execute(statement,(person_id,start_date)).fetchone()
    return result[0]

def updateattendance(person_id,cur_date):
    
    if cur_date.weekday() == 6:
        cur_date += timedelta(days=1)
    
    df = pd.read_csv("Book1.csv")
    userindex = df.index[df['user_id']==person_id].tolist()[0]
    
    while cur_date.weekday() != 5:
        df.loc[userindex,cur_date.strftime('%d/%m/%Y').replace('/0','/')] = 1
        cur_date += timedelta(days=1)

    df.to_csv('Book1.csv',index=False)
    return 


def updateMCattendance(person_id,startdate,enddate):
    df = pd.read_csv('Book1.csv')
    userindex = df.index[df['user_id']==person_id].tolist()[0]
    cur_date = startdate

    if cur_date.weekday() == 6:
        cur_date += timedelta(days=1)

    #check if enddate will be next week or this week
    if cur_date.isocalendar()[1] == enddate.isocalendar()[1]:
        to_edit = True
    else:
        to_edit = False

    print(cur_date)
    while cur_date <= enddate:
        df.loc[userindex,cur_date.strftime('%d/%m/%Y').replace('/0','/')] = 0
        cur_date += timedelta(days=1)
    df.to_csv('Book1.csv',index=False)
    if to_edit: # if same week and need to "bookin" for the remainding days 
        updateattendance(person_id,cur_date)
    return


def checkoncourse2(person_id):
    con = sqlite3.connect(DB_NAME)
    result = con.execute("select Cadets.on_course from Cadets inner join registered_ids on registered_ids.fd_no = Cadets.fd_no where registered_ids.user_id = (?)",(person_id,)).fetchone()
    con.close()
    return result[0] if result else 0


def getattendance(cur_date):
    df = pd.read_csv('Book1.csv')
    cur_date_str = cur_date.strftime('%d/%m/%Y').replace('/0','/')
    cur_attd = 0
    total_strength = 0
    for i in range(len(df)):
        #check if in course 
        # print(type(df.loc[i,'user_id']))
        if checkoncourse2(int(df.loc[i,'user_id'])):
            if df.loc[i,cur_date_str] == 1:
                cur_attd+=1 
            total_strength+=1
    ret = [cur_attd,total_strength]
    return ret

def generate_attd(cur_date):
    df = pd.read_csv('Book1.csv')
    cur_date_str = cur_date.strftime('%Y-%m-%d')
    ret = '**SCTW**\n'
    count = 1
    con = sqlite3.connect(DB_NAME)
    perm_staffs = con.execute('select * from Perm_staff').fetchall()
    for staff in perm_staffs:
        name,rank = staff
        x = f'✔ {count}. {rank} {name}\n'
        ret+=x
        count += 1
    
    ret += f'\n{COURSE_NAME}\n'
    cur_attd,total_strength = getattendance(cur_date)
    ret += f'{cur_attd}/{total_strength}\n'

    count = 1
    mc_status = con.execute("""select Cadets.fd_no,Cadets.name,cadet_status.start_date,cadet_status.end_date, Cadets.rank from cadet_status inner join
registered_ids on registered_ids.user_id = cadet_status.user_id inner join
Cadets on registered_ids.fd_no = Cadets.fd_no where cadet_status.end_date >= (?) and cadet_status.start_date <= (?) and Cadets.on_course = 1 order by Cadets.fd_no ASC""",(cur_date_str,cur_date_str)).fetchall()
    for row in mc_status:
        fd_no, name, start, end,crank = row
        start = datetime.strptime(start,'%Y-%m-%d').date()
        start_str = start.strftime('%d%m%Y')
        end = datetime.strptime(end,'%Y-%m-%d').date()
        end_str = end.strftime('%d%m%Y')
        ret += f'{count}. {fd_no} {crank} {name} (MC, {start_str}-{end_str})\n'


    leave_status = con.execute("""select Cadets.fd_no,Cadets.name,cadet_leave.start_date,cadet_leave.end_date, Cadets.rank from cadet_leave inner join
registered_ids on registered_ids.user_id = cadet_leave.user_id inner join
Cadets on registered_ids.fd_no = Cadets.fd_no where cadet_leave.end_date >= (?) and cadet_leave.start_date <= (?) and Cadets.on_course = 1 order by Cadets.fd_no ASC""",(cur_date_str,cur_date_str)).fetchall()
    
    for row in leave_status:
        fd_no, name, start, end,crank = row
        start = datetime.strptime(start,'%Y-%m-%d').date()
        start_str = start.strftime('%d%m%Y')
        end = datetime.strptime(end,'%Y-%m-%d').date()
        end_str = end.strftime('%d%m%Y')
        ret += f'{count}. {fd_no} {crank} {name} (Leave: {start_str}-{end_str})\n'


    return ret

def generate_pstate(cur_date: date,num_platoons):
    con = sqlite3.connect(DB_NAME)
    cur_date_str = cur_date.strftime('%Y-%m-%d')
    ret = f"{cur_date.strftime('%d%m%Y')}\n"
    cur_strength, total_strength = getattendance(cur_date)
    ret += f'Total Strength: {total_strength}\nCurrent: {cur_strength}\nPresent:\n\n\n'


    mc_list = con.execute("""select Cadets.fd_no,Cadets.name,cadet_status.start_date,cadet_status.end_date, Cadets.rank from cadet_status inner join
registered_ids on registered_ids.user_id = cadet_status.user_id inner join
Cadets on registered_ids.fd_no = Cadets.fd_no where cadet_status.end_date >= (?) and cadet_status.start_date <= (?) and Cadets.on_course = 1 order by Cadets.fd_no ASC""",(cur_date_str,cur_date_str)).fetchall()
    
    leave_list = con.execute("""select Cadets.fd_no,Cadets.name,cadet_leave.start_date,cadet_leave.end_date, Cadets.rank from cadet_leave inner join
registered_ids on registered_ids.user_id = cadet_leave.user_id inner join
Cadets on registered_ids.fd_no = Cadets.fd_no where cadet_leave.end_date >= (?) and cadet_leave.start_date <= (?) and Cadets.on_course = 1 order by Cadets.fd_no ASC""",(cur_date_str,cur_date_str)).fetchall()

    temp_status_list = con.execute("""select Cadets.fd_no, Cadets.name, temp_status.status, temp_status.start_date, temp_status.end_date, Cadets.rank 
from Cadets inner join registered_ids on Cadets.fd_no = registered_ids.fd_no inner join temp_status on temp_status.user_id = registered_ids.user_id 
where temp_status.end_date >= (?) and temp_status.start_date<= (?) and Cadets.on_course = 1 order by Cadets.fd_no ASC""",(cur_date_str,cur_date_str)).fetchall()

    print(mc_list)
    for i in range(num_platoons):
        to_ins = f'PLT {i+1}\n'
        current_p, total_pstrength = get_platoon_attendance(cur_date,i+1)
        to_ins += f'Total: {total_pstrength}\nCurrent: {current_p}\n'
        #get ATT C
        p_attc_count = 0
        mc_str = ''
        status_str = ''
    
        for row in mc_list:
            fd_no, name, start, end, rank = row
            start = datetime.strptime(start,'%Y-%m-%d').date()
            start_str = start.strftime('%d%m%Y')
            end = datetime.strptime(end,'%Y-%m-%d').date()
            end_str = end.strftime('%d%m%Y')
            if (i+1) == getplatoon(fd_no):
                p_attc_count += 1
                mc_str += f'{fd_no} {rank} {name}\n(MC {start_str}-{end_str})\n\n'
            
        for row in leave_list:
            
            fd_no, name, start, end, rank = row
            start = datetime.strptime(start,'%Y-%m-%d').date()
            start_str = start.strftime('%d%m%Y')
            end = datetime.strptime(end,'%Y-%m-%d').date()
            end_str = end.strftime('%d%m%Y')
            if (i+1) == getplatoon(fd_no):
                p_attc_count += 1
                mc_str += f'{fd_no} {rank} {name}\n(Leave {start_str}-{end_str})\n\n'

        mc_str = f'ATT C: {p_attc_count}\n\n' + mc_str

        #getstatus
        p_status_count = 0
        added = []
        temp_str = ''
    
        for row in temp_status_list:
            fd_no,name,cstatus,start,end,rank = row
            start = datetime.strptime(start,'%Y-%m-%d').date()
            start_str = start.strftime('%d%m%Y')
            end = datetime.strptime(end,'%Y-%m-%d').date()
            end_str = end.strftime('%d%m%Y')
            if (i+1) == getplatoon(fd_no):
                if name in added:
                    temp_str += f'Status: {cstatus} from {start_str}-{end_str}\n'
                elif name not in added:
                    status_str += temp_str
                    temp_str = f'{fd_no} {rank} {name}\nStatus: {cstatus} from {start_str}-{end_str}\n'
                    added.append(name)
                    p_status_count += 1

            status_str += temp_str + '\n'

        status_str = f'STATUS: {p_status_count}\n\n' + status_str


        to_ins += mc_str + status_str
        ret += to_ins
    return ret

def getplatoon(fd_no):
    return int((str(fd_no))[0])


def get_platoon_attendance(cur_date,platoon):
    df = pd.read_csv('Book1.csv')
    cur_date_str = cur_date.strftime('%d/%m/%Y').replace('/0','/')
    cur_attd,total_pstrength = 0,0
    for i in range(len(df)):
        #check if they oncourse, check their platoon
        if checkoncourse2(int(df.loc[i,'user_id'])) and checkplatoon(int(df.loc[i,'user_id']),platoon):
            if df.loc[i,cur_date_str] == 1:
                cur_attd += 1
            total_pstrength += 1
    return [cur_attd,total_pstrength]

def checkplatoon(person_id,platoon):
    con = sqlite3.connect(DB_NAME)
    fd_no = con.execute("select Cadets.fd_no from Cadets inner join registered_ids on registered_ids.fd_no = Cadets.fd_no where registered_ids.user_id = (?)",(person_id,)).fetchone()
    if fd_no:
        return platoon == getplatoon(fd_no[0])
    else:
        return False
    

def verifyloc(lat,long,camp):
    bound_list = camp_bounds[camp]
    lat_list, long_list = bound_list
    if lat >= min(lat_list) and lat <= max(lat_list) and long >= min(long_list) and long <= max(long_list):
        return True
    return False


#----------------------------misc commands ------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""Welcome to rayyantest3bot
/start - Starts the bot
/register - Register yourself
/bookin - Book in
/not_bookin - If you are unable to bookin, use this command to submit your reason / Register your MC or LEAVE
/editstatus - Edit your current MC or LEAVE status
/generate -  Generate parade state [Includes Perm Staff] ( FOR 10/23 AISCC CURRENTLY )
/add_temp_status - Submit your temporary status such as RMJ/Heavy Load/Upper Limb
/updateooc - Submit Cadet's 4D to OOC from course
/generate_cadet_pstate - Generate Cadet Parade State for platoons""")
    
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Available commands are:\n/register\n/bookin\n/not_bookin (If you are unable to bookin)")



#---------------------register---------------------------


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if notinDB(update.message.chat.id):
        await update.message.reply_text("Send your 4D Number (4 Digits)\n\nSend /cancel_reg to stop registering")
        return FD_NO
    else:
        await update.message.reply_text("You have already registered! If you would like to change your information, please let your commander know")
        return ConversationHandler.END

async def fd_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    fd_no = update.message.text
    user_data["fd_no"] = fd_no
    await update.message.reply_text(f"Your 4D number is {fd_no}.\n\nPlease enter your name!")
    return NAME

async def user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_name = update.message.text
    user_data["user_name"] = user_name
    await update.message.reply_text(f'Your name is {user_name}\n\nPlease enter your masked NRIC in format: eg. TXXXX123A')
    return MASKED_IC

async def masked_ic(update:Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    maskedic = update.message.text
    user_data["maskedic"] = maskedic.upper()
    await update.message.reply_text(f"Your masked NRIC is {maskedic}!\n\nPlease enter your Rank! eg. SCT/OCT/3SG ")
    return REG_COMPLETE

async def reg_complete(update: Update,context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data['rank'] = update.message.text
    con = sqlite3.connect(DB_NAME)

    con.execute("insert into Cadets values(?,?,?,?,?)",(user_data["fd_no"],user_data['user_name'],user_data['maskedic'],user_data['rank'],True))
    con.execute("insert into registered_ids values (?,?)", (update.message.chat.id, user_data['fd_no']))
    con.commit()
    con.close()
    print(f"Successfully inserted {user_data['user_name']}'s data into the database")
    await update.message.reply_text("You have registered successfully!")

    with open('Book1.csv','r+') as f1:
        headers = f1.readline().split(',')
        to_insert = f'{update.message.chat.id},{user_data["user_name"]}' + ',0'*(len(headers)-2) +'\n'
        f1.write(to_insert)
        print('Inserted into excel')


    return ConversationHandler.END


async def cancel_reg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    user_data.clear()
    print(user_data)
    await update.message.reply_text("Registration cancelled, Bye bye")
    return ConversationHandler.END



#----------------------------------bookin-----------------------------------
async def bookin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    BUTTON1 = KeyboardButton("Send Location", request_location=True)
    BUTTON2 = KeyboardButton("/cancelbookin")
    reply_keyboard = [[BUTTON1,BUTTON2]]
    await update.message.reply_text("Please send your current location!", reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))
    return LOCATION

async def check_location(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # do conditional check on the location with coordinates


    name = getusername(update.message.chat.id)
    print(f"{name} is at {update.message.location}")

    loc = update.message.location
    if verifyloc(loc.latitude,loc.longitude,"Pasir Laba"): # make sure "Pasir Laba" is changed with relevant camp...assuming this would be used by other camps.. probably not XD

        await update.message.reply_text("You have booked in successfully ✔!",reply_markup=ReplyKeyboardRemove())
        updateattendance(update.message.chat.id,date.today())
    else: 
        await update.message.reply_text("You are not within the area of your camp. Please enter your camp before using the book in function!")
    return ConversationHandler.END


async def not_bookin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    BUTTON1 = KeyboardButton("I am on MC")
    BUTTON2 = KeyboardButton("Leave")
    BUTTON3 = KeyboardButton('/cancelbookin')
    reply_keyboard = [[BUTTON1,BUTTON2,BUTTON3]]
    await update.message.reply_text("Why are you not booking in today?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return NOTBOREASON

async def bookin_mc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    if update.message.text == "I am on MC":
        userdata["STATE"] = "MC"
    elif update.message.text == "Leave":
        userdata["STATE"] = "LEAVE"
    await update.message.reply_text("Please enter your start date in format (dd-mm-yyyy): [or type /cancelbookin to cancel]",reply_markup= ReplyKeyboardRemove())
    return NOTBOREASON2

async def bookin_mc2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    DATESTART = update.message.text
    userdata = context.user_data
    if userdata["STATE"] == "MC":
        userdata["MCSTART"] = datetime.strptime(DATESTART,'%d-%m-%Y').date()
    elif userdata["STATE"] == "LEAVE":
        userdata["LEAVESTART"] = datetime.strptime(DATESTART,'%d-%m-%Y').date()
    await update.message.reply_text("Please enter your end date in format (dd-mm-yyyy): [or type /cancelbookin to cancel]")
    return NOTBOREASON3

async def bookin_mc3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    DATEEND = update.message.text
    userdata = context.user_data
    if userdata["STATE"] == "MC":
        userdata["MCEND"] = datetime.strptime(DATEEND,'%d-%m-%Y').date()
    elif userdata["STATE"] == "LEAVE":
        userdata["LEAVEEND"] = datetime.strptime(DATEEND,'%d-%m-%Y').date()
    #need to update into excel that stores it.
    con = sqlite3.connect(DB_NAME)
    if userdata['STATE'] == 'MC':
        con.execute('insert into cadet_status values (?,?,?)',(update.message.chat.id,userdata["MCSTART"].strftime('%Y-%m-%d'),userdata["MCEND"].strftime('%Y-%m-%d')))
        startdate = userdata["MCSTART"]
        enddate = userdata["MCEND"]
        
        await update.message.reply_text(f"Your MC status is: {userdata['MCSTART'].strftime('%d-%m-%Y')} to {userdata['MCEND'].strftime('%d-%m-%Y')} (inclusive)\n\nYou have successfully store your MC status. To edit it, please use command /editstatus!")
    elif userdata['STATE'] == 'LEAVE':
        con.execute('insert into cadet_leave values (?,?,?)',(update.message.chat.id,userdata["LEAVESTART"].strftime('%Y-%m-%d'),userdata["LEAVEEND"].strftime('%Y-%m-%d')))
        startdate = userdata["LEAVESTART"]
        enddate = userdata["LEAVEEND"]
        await update.message.reply_text(f"Your LEAVE status is: {userdata['LEAVESTART'].strftime('%d-%m-%Y')} to {userdata['LEAVEEND'].strftime('%d-%m-%Y')} (inclusive)\n\nYou have successfully store your LEAVE status. To edit it, please use command /editstatus!")
    con.commit()
    con.close()
    print(f'{userdata["STATE"]} status of {update.message.from_user.name} successfully inserted')

    ## insert into excel sheet
    updateMCattendance(update.message.chat.id,startdate,enddate)
    del userdata["STATE"]
   
    return ConversationHandler.END

async def cancelbookin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Book In Cancelled!",reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


#-----------------------------------editinfo--------------------------------------

async def editstatus_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    BUTTON1 = KeyboardButton("Edit MC status")
    BUTTON2 = KeyboardButton("Edit Leave status")
    reply_keyboard = [[BUTTON1,BUTTON2]]
    await update.message.reply_text("Which status would you like to update?", reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))
    return GETSTATUSSTART


async def editstatus_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    if update.message.text == "Edit MC status":
        userdata["EDITSTATE"] = "MC"
    else:
        userdata['EDITSTATE'] = 'LEAVE'
    await update.message.reply_text(f"Please enter the start date of the {userdata['EDITSTATE']} which you previously submitted\nFor example, you registered 11-06-2023 as the start date for your most recent {userdata['EDITSTATE']}\n\nIf you wish to cancel, send /canceledit")
    return CHECKVALIDSTATUS


async def editstatus_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat.id
    start_date =datetime.strptime(update.message.text,'%d-%m-%Y').date()
    start_date_str = start_date.strftime('%Y-%m-%d')
    userdata = context.user_data
    userdata['DBTOCHECK'] = 'cadet_status' if userdata['EDITSTATE'] == 'MC' else 'cadet_leave'

    if not checkstatus(user_id,start_date_str,userdata['DBTOCHECK']):
        await update.message.reply_text(f"You currently do not have any {userdata['EDITSTATE']} status registered with date starting from {update.message.text} .\nTo register your {userdata['EDITSTATE']} type /not_bookin")
        return ConversationHandler.END
    else:
        end_date_str = getenddate(user_id,start_date_str,userdata['DBTOCHECK'])
        end_date = datetime.strptime(end_date_str,'%Y-%m-%d').date()
        await update.message.reply_text(f"Your {userdata['EDITSTATE']} status currently is {start_date_str} to {end_date_str} (inclusive).\n"
                                        "Enter the new end date to change to in the format (dd-mm-yyyy): ( type /canceledit to stop editting ) ")
        
        if userdata['EDITSTATE'] == 'MC':
            userdata['MCSTART'] = start_date
        else:
            userdata['LEAVESTART'] = start_date

        print(f'State is: {userdata["EDITSTATE"]}')
        return EDITSTATUS

async def editstatus_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_end_date = datetime.strptime(update.message.text,'%d-%m-%Y').date()
    new_end_date_str = new_end_date.strftime('%Y-%m-%d')
    userdata = context.user_data
    state = userdata['EDITSTATE']
    if state == 'MC':
        userdata["MCEND"] = new_end_date
        start_date = userdata['MCSTART']
        start_date_str = start_date.strftime('%Y-%m-%d')
    
    else:
        userdata['LEAVEEND'] = new_end_date
        start_date = userdata['LEAVESTART']
        start_date_str = start_date.strftime('%Y-%m-%d')
    #update in DB

    con = sqlite3.connect(DB_NAME)
    statement = f"update {userdata['DBTOCHECK']} set end_date = (?) where user_id = (?) and start_date = (?)"
    con.execute(statement,(new_end_date.strftime('%Y-%m-%d'),update.message.chat.id,start_date_str))
    con.commit()
    print("Update successful")
    con.close()
    await update.message.reply_text(f"You have successfully changed your {state} status to be from {start_date_str} to {new_end_date_str} (inclusive)!")

    # change excel to reflect the updated dates

    updateMCattendance(update.message.chat.id,start_date,new_end_date)
    del userdata["EDITSTATE"]

    return ConversationHandler.END


async def canceledit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("You have cancelled editing!")  
    return ConversationHandler.END


#---------------generate-----------------------------


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    message = generate_attd(date.today())
    await update.message.reply_text(message)


async def generate_cadet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = generate_pstate(date.today(),NUM_PLATOONS)
    await update.message.reply_text(message)

#------------------update as OOC------------------------

async def updateOOC(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter the 4D number of the cadet who has OOC'ed. If you are unsure of the Cadet's 4D number, please go to the database under table Cadets. To cancel updating, type /canceledit")
    return UPDATEOOC2

async def updateOOC2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cadet_name = getusername2(update.message.text)
    userdata = context.user_data
    if cadet_name:
        if checkoncourse(update.message.text):
            userdata['to_ooc'] = update.message.text
            BUTTON1 = KeyboardButton('Yes')
            BUTTON2 = KeyboardButton('No')
            reply_keyboard = [[BUTTON1,BUTTON2]]
            await update.message.reply_text(f"The cadet you have selected is {cadet_name}, would you like to proceed to OOC {cadet_name}?", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return UPDATEOOC3
        else:
            await update.message.reply_text("Cadet you have selected is already out of course! Byebyes")
            return ConversationHandler.END
    else:
        await update.message.reply_text(f"Cadet of 4D number: {update.message.text} is not found, please check the database again!  Type /updateooc again to OOC a cadet!")
        return ConversationHandler.END
    
async def updateOOC3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    if update.message.text == 'Yes':
        #get new rank
        await update.message.reply_text(f"Enter the new rank given to the Cadet!",reply_markup=ReplyKeyboardRemove())
        return UPDATEOOC4
    else:
        del userdata['to_ooc']
        await update.message.reply_text("Operation cancelled. Bye bye!")
        return ConversationHandler.END
    
async def updateOOC4(update:Update,context:ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    new_rank = update.message.text
    con = sqlite3.connect(DB_NAME)
    con.execute("update Cadets set rank = (?), on_course = (?) where fd_no = (?)",(new_rank,False,userdata['to_ooc']))
    con.commit()
    print("OOC update successfully")
    await update.message.reply_text(f"You have successfully OOC'ed {getusername2(userdata['to_ooc'])} from the course!")
    return ConversationHandler.END



#-----------------temp_status--------------------------- (Main idea is for the paradestate of CADETS daily...used by SGTs or DT)

    #For this function it is to track the status of cadets.
    #Store status by status, basically for each status they need to add in one by one I.E /temp_status for each status
    #How i am planning on retrieving the information is: sql query to store each and every status currently by cadets and their respective time frame
    #create dict, for each cadet num, stores a list of lists hence -> [[Status,start,end],...] 
    #do the necessary concat to generate CADETparade state for FP n LP if required, in another function..

async def temp_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'Register your current statuses, for each status, run this command to register it into the system!\n\nPlease enter a status or send /cancelupdate to cancel:  ')
    return TEMPSTATUS2

async def temp_status2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    userdata['temp_status'] = update.message.text
    await update.message.reply_text(f'Please enter the start date of your status: {userdata["temp_status"]} in the format (dd-mm-yyyy): ')
    return TEMPSTATUS3

async def temp_status3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    temp_start = datetime.strptime(update.message.text,'%d-%m-%Y').date()
    userdata['temp_status_start'] = temp_start
    await update.message.reply_text(f'Please enter the end date of your status: {userdata["temp_status"]} in the format (dd-mm-yyyy): ')
    return TEMPSTATUS4

async def temp_status4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    temp_end = datetime.strptime(update.message.text,'%d-%m-%Y').date()
    userdata['temp_status_end'] = temp_end
    #update into db
    con = sqlite3.connect(DB_NAME)
    con.execute("insert into temp_status values (?,?,?,?)",(update.message.chat.id,userdata['temp_status'],userdata['temp_status_start'].strftime('%Y-%m-%d'),userdata['temp_status_end'].strftime('%Y-%m-%d')))
    con.commit()
    await update.message.reply_text(f'You have successfully submitted your status: {userdata["temp_status"]} from {userdata["temp_status_start"]}-{userdata["temp_status_end"]} inclusive into the database')

    userdata.clear()
    return ConversationHandler.END

async def cancelupdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = context.user_data
    await update.message.reply_text(f"Submitting of status has been cancelled. To submit again type /add_temp_status")
    userdata.clear()
    return ConversationHandler.END

#------------------error handler------------------------

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')


#--------------------driver---------------------------

if __name__ == "__main__":
    print(f"Starting {BOT_USERNAME}")
    app = Application.builder().token(TOKEN).build()

    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("register",register)],
        states= {
            FD_NO: [MessageHandler(filters.Regex("^\d{4}$") & ~filters.COMMAND,fd_no)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND ,user_name)],
            MASKED_IC: [MessageHandler(filters.Regex("^[TtSs](XXXX)\d{3}[a-zA-Z]$"),masked_ic)],
            REG_COMPLETE: [MessageHandler(filters.Regex("(?<!\w)\w{3}(?!\w)"),reg_complete)]

        },
        fallbacks= [CommandHandler("cancel_reg",cancel_reg)])
    
    bookin_handler = ConversationHandler(
        entry_points=[CommandHandler("bookin",bookin)],
        states={
            LOCATION: [MessageHandler(filters.LOCATION,check_location)],
        },
         fallbacks= [CommandHandler('cancelbookin',cancelbookin)]
    )
    
    no_bookin_handler = ConversationHandler(
        entry_points=[CommandHandler('not_bookin',not_bookin)],
        states=
            {NOTBOREASON: [MessageHandler(filters.Regex('^(I am on MC|Leave)'),bookin_mc)],
             NOTBOREASON2: [MessageHandler(filters.Regex(DATE_REGEX),bookin_mc2)],
             NOTBOREASON3: [MessageHandler(filters.Regex(DATE_REGEX),bookin_mc3)]
            },
            fallbacks=[CommandHandler('cancelbookin',cancelbookin)]
    )

    editstatus_handler = ConversationHandler(
        entry_points=[CommandHandler('editstatus',editstatus_option)],
        states=
        {
            GETSTATUSSTART: [MessageHandler(filters.Regex('^(Edit MC status|Edit Leave status)'),editstatus_start)],
            CHECKVALIDSTATUS: [MessageHandler(filters.Regex(DATE_REGEX),editstatus_check)],
            EDITSTATUS: [MessageHandler(filters.Regex(DATE_REGEX),editstatus_db)]
        },
        fallbacks=[CommandHandler('canceledit',canceledit)]

    )

    updateooc_handler = ConversationHandler(

        entry_points=[CommandHandler('updateooc',updateOOC)],
        states = 
        {
            UPDATEOOC2: [MessageHandler(filters.Regex("^\d{4}$"),updateOOC2)],
            UPDATEOOC3: [MessageHandler(filters.Regex("^(Yes|No)"),updateOOC3)],
            UPDATEOOC4: [MessageHandler(filters.Regex("(?<!\w)\w{3}(?!\w)"),updateOOC4)]
        },
        fallbacks=[CommandHandler('canceledit',canceledit)]
    )


    tempstatus_handler = ConversationHandler(

        entry_points=[CommandHandler("add_temp_status", temp_status)],
        states=
        {
            TEMPSTATUS2: [MessageHandler(filters.TEXT & ~filters.COMMAND,temp_status2)],
            TEMPSTATUS3: [MessageHandler(filters.Regex(DATE_REGEX),temp_status3)],
            TEMPSTATUS4: [MessageHandler(filters.Regex(DATE_REGEX),temp_status4)]
        },
        fallbacks=[CommandHandler('cancelupdate',cancelupdate)]

    )


    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("help",help))
    app.add_error_handler(error)
    app.add_handler(reg_handler)
    app.add_handler(bookin_handler)
    app.add_handler(editstatus_handler)
    app.add_handler(no_bookin_handler)
    app.add_handler(CommandHandler('generate',generate))
    app.add_handler(CommandHandler('generate_cadet_pstate',generate_cadet))
    app.add_handler(updateooc_handler)
    app.add_handler(tempstatus_handler)
    print("Polling")
    app.run_polling()