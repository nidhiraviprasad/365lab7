import getpass
import mysql.connector
import datetime
from decimal import Decimal
import pandas as pd
import warnings

warnings.filterwarnings('ignore')




def connect():
    db_password = getpass.getpass()
    conn = mysql.connector.connect(user='nravipra', password=db_password,
                               host='mysql.labthreesixfive.com',
                               database='nravipra')
    return conn




# view popular rooms
# TODO: format this table nicely with headers for each column
def fr1(conn):
    print("Here are our rooms, sorted by popularity: ")
    query = """
                   
SELECT r.RoomCode, r.RoomName, r.Beds, r.bedType, r.maxOcc, r.basePrice, r.decor,
    ROUND(
        (SELECT SUM(DATEDIFF((CASE WHEN rsv.Checkout > CURDATE() THEN CURDATE() 
                                   ELSE rsv.Checkout END),
                              (CASE WHEN rsv.CheckIn < CURDATE() - INTERVAL 180 DAY THEN CURDATE() - INTERVAL 180 DAY
                                   ELSE rsv.CheckIn END)))
            from lab7_reservations rsv
            WHERE rsv.Room = r.RoomCode 
            and (CASE WHEN rsv.Checkout > CURDATE() THEN CURDATE() 
                                   ELSE rsv.Checkout END) >= 
                (CASE WHEN rsv.CheckIn < CURDATE() - INTERVAL 180 DAY THEN CURDATE() - INTERVAL 180 DAY
                                   ELSE rsv.CheckIn END)
        ) / 180, 2
    ) as Popularity,
    (
        SELECT MIN(rsv.Checkout)
        from lab7_reservations rsv
        WHERE rsv.Room = r.RoomCode 
        and rsv.Checkout > CURDATE()
    ) AS NextAvailability,
    (
        SELECT DATEDIFF(rsv.CheckOut, rsv.CheckIn)
        from lab7_reservations rsv
        WHERE rsv.Room = r.RoomCode
        and rsv.Checkout = (
            SELECT MAX(rsv.Checkout)
            from lab7_reservations rsv
            WHERE rsv.Room = r.RoomCode
            and rsv.Checkout <= CURDATE()
        )
    ) AS PreviousStayLength,
    
    (SELECT MAX(rsv.Checkout)
     from lab7_reservations rsv
     WHERE rsv.Room = r.RoomCode 
     and rsv.Checkout <= CURDATE()) AS RecentCheckoutDate

from lab7_rooms r
ORDER BY Popularity desc;
                   
                   """
    result = pd.read_sql(query, conn)
    print(result)
    conn.commit()







# make a reservation
# TODO: format the available rooms nicely to the user (in a table format with headers for each column)
def fr2(conn):
    print("Please enter the following information to make your reservation: ")
    f_name = input("First name: ").strip()
    l_name = input("Last name: ").strip()
    code = input("Room code (enter 'Any' if you have no preference): ").strip()
    bed = input("Bed type (enter 'Any' if you have no preference): ").strip()
    checkin = input("Check in date (MM/DD/YYYY): ").strip()
    checkout = input("Check out date (MM/DD/YYYY): ").strip()
    adults = input("Number of adults: ").strip()
    children = input("Number of children: ").strip()

    # perform input validation here before continuing with query
    checkin = checkin.split('/')
    checkout = checkout.split('/')
    checkin = datetime.date(int(checkin[2]), int(checkin[0]), int(checkin[1]))
    checkout = datetime.date(int(checkout[2]), int(checkout[0]), int(checkout[1]))

    if (checkin > checkout):
        print("Invalid dates: checkin date is after checkout date")
        return
    
    if (not children.isnumeric() or not adults.isnumeric()):
        print("Please only provide numbers for the number of adults/children categories")
        return
    numOccupants = int(children) + int(adults)
    
    ci = checkin.strftime("%Y-%m-%d")
    co = checkout.strftime("%Y-%m-%d")

    room_details = pd.read_sql("""
select *
from lab7_rooms r
where (r.RoomCode = %s or %s = 'Any' or %s = '')
and (r.bedType = %s or %s = 'Any' or %s = '')
and r.maxOcc >= %s
and ( 
    select count(*)
    from lab7_reservations res
    join lab7_rooms r on r.RoomCode = res.Room
    where (r.RoomCode = %s)
    and (
        (res.CheckIn >= %s and res.Checkout < %s) or
        (res.CheckIn <= %s and res.Checkout > %s) or
        (res.CheckIn <= %s and res.Checkout > %s)
        )
    ) = 0;
                   """, conn, params=(code, code, code, bed, bed, bed, numOccupants, code, ci, co, co, co, ci, ci))
    
    if (not room_details.empty):
        print("\nHere are all the rooms available according to your criteria: \n")
        room_details.index = room_details.index + 1
        print(room_details)
        room = input("\nWhich of the above rooms would you like to book? Please enter the option number: ")
        while not room.isnumeric() or int(room) > len(room_details) or int(room) < 1:
            room = input("Invalid room selection. Please select from the given options: ")
        room = int(room) - 1

        basePrice = float(room_details.iloc[room, 5])

        result = pd.read_sql("""
select max(CODE) from lab7_reservations;
                       """, conn)
        if not result.empty:
            newCode = str(result.iloc[0, 0] + 1)
        else:
            newCode = 1

        numWeekdays = 0
        numWeekends = 0
        currentDate = checkin
        delta = datetime.timedelta(days=1)
        while currentDate < checkout:
            if currentDate.weekday() > 4:
                numWeekends += 1
            else:
                numWeekdays +=1
            currentDate += delta
        
        costOfStay = basePrice * numWeekdays + basePrice * 1.1 * numWeekends

        cursor = conn.cursor()
        cursor.execute("""
insert into lab7_reservations 
(CODE, Room, CheckIn, Checkout, Rate, LastName, FirstName, Adults, Kids)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                       """, [newCode, room_details.iloc[room, 0], ci, co, Decimal(costOfStay), l_name, f_name, int(adults), int(children)])
        res = cursor.fetchall()
        cursor.close()
        
        print(f"\nConfirmed! {f_name} {l_name} has booked room {room_details.iloc[room, 0]}: {room_details.iloc[room, 1]}." +
              f"\nBed type: {room_details.iloc[room, 3]}" +
              f"\nDates: {ci} to {co}" +
              f"\nOccupants: {adults} adults and {children} children" +
              f"\nTotal cost: ${costOfStay:.2f}" + 
              f"\nConfirmation code: {newCode}\n")
        
            
    else:

        result = pd.read_sql("""
select count(*)
from lab7_rooms r
where (r.maxOcc >= %s);
                       """, conn, params=(str(numOccupants),))
        if (result.iloc[0, 0] == 0):
            print("Unfortunately, the number of people you are making a reservation for exceeds the maximum occupancy of all available rooms.")
            return

        
        alternate_rooms = pd.read_sql("""
select r.*
from lab7_rooms r
where r.maxOcc >= %s
and (
    select count(*)
    from lab7_reservations res
    join lab7_rooms r on r.RoomCode = res.Room
    where (r.RoomCode = %s)
    and (
        (res.CheckIn >= %s and res.Checkout < %s) or
        (res.CheckIn <= %s and res.Checkout > %s) or
        (res.CheckIn <= %s and res.Checkout > %s)
        )
) = 0
order by abs(r.basePrice - 
    coalesce((select basePrice from lab7_rooms where RoomCode = %s), 0)
);
                   """, conn, params=(str(numOccupants), code, ci, co, ci, ci, co, co, code))
    

        print("\nUnfortunately, we were not able to find any rooms according to your criteria. Here are some similar rooms you can reserve: \n")
        alternate_rooms.index = alternate_rooms.index + 1
        print(alternate_rooms)

        confirmation = input("\nWould you like to book any of the above rooms? [Y to confirm; any other key to cancel] " ).strip()
        if (not confirmation == 'Y' and not confirmation == 'y'):
            print("No booking was made. ")
            return
        
        room = input("\nWhich of the above rooms would you like to book? Please enter the option number: ")
        while not room.isnumeric() or int(room) > min(5, len(alternate_rooms)) or int(room) < 1:
            room = input("Invalid room selection. Please select from the given options: ")
        room = int(room) - 1


        basePrice = float(alternate_rooms.iloc[room, 5])

        result = pd.read_sql("""
select max(CODE) from lab7_reservations;
                       """, conn)
        if result.empty:
            newCode = 1
        else:
            newCode = str(result.iloc[0, 0] + 1)

        numWeekdays = 0
        numWeekends = 0
        currentDate = checkin
        delta = datetime.timedelta(days=1)
        while currentDate < checkout:
            if currentDate.weekday() > 4:
                numWeekends += 1
            else:
                numWeekdays +=1
            currentDate += delta
        
        costOfStay = basePrice * numWeekdays + basePrice * 1.1 * numWeekends

        pd.read_sql("""
insert into lab7_reservations 
(CODE, Room, CheckIn, Checkout, Rate, LastName, FirstName, Adults, Kids)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                       """, conn, params=(newCode, alternate_rooms.iloc[room, 0], ci, co, Decimal(costOfStay), l_name, f_name, int(adults), int(children)))
        
        
        print(f"\nConfirmed! {f_name} {l_name} has booked room {alternate_rooms.iloc[room, 0]}: {alternate_rooms.iloc[room, 1]}." +
              f"\nBed type: {alternate_rooms.iloc[room, 3]}" +
              f"\nDates: {ci} to {co}" +
              f"\nOccupants: {adults} adults and {children} children" +
              f"\nTotal cost: ${costOfStay:.2f}" + 
              f"\nConfirmation code: {newCode}\n")

    
    conn.commit()







# cancel a reservation
# TODO: format the reservation details nicely when printed out to user
def fr3(conn):
    code = input("Please enter the reservation code for the reservation you would like to cancel: ").strip()
    cursor = conn.cursor()

    result = pd.read_sql("""
SELECT *
from lab7_reservations
WHERE CODE = %s
                   """, conn, params = (code, ))
    
    if (not result.empty):
        print("Reservation details: ")
        print(result)
        confirmation = input("Are you sure you would like to cancel the above reservation? [Y to confirm; any other key to cancel] " ).strip()
        if (confirmation == 'Y' or confirmation == 'y'):
            cursor.execute("""
DELETE
from lab7_reservations
WHERE CODE = %s
                   """, [code])
            print(f"Your reservation {code} was cancelled successfully. ")
        else:
            print("Your reservation was not cancelled. ")
    else:
        print("Your reservation with code", code, "was not found in the system. ")
    conn.commit()
    cursor.close()









# view reservation details
def fr4(conn):
    print("Enter the following information to look up reservation details: ")
    f_name = input("First name: ").strip()
    l_name = input("Last name: ").strip()
    start = input("Start date (MM/DD/YYYY): ").strip()
    end = input("End date (MM/DD/YYYY): ").strip()
    code = input("Room code: ").strip()
    res_code = input("Reservation code: ").strip()

    s_date = 0
    e_date = 0

    if (not start == ''):
        start = start.split('/')
        start = datetime.date(int(start[2]), int(start[0]), int(start[1]))
        s_date = start.strftime("%Y-%m-%d")
    if (not end == ''):
        end = end.split('/')
        end = datetime.date(int(end[2]), int(end[0]), int(end[1]))
        e_date = end.strftime("%Y-%m-%d")

    result = pd.read_sql("""
select * from lab7_reservations res
join lab7_rooms r on r.RoomCode = res.Room
where (res.FirstName like concat('%', concat(%s, '%')) or %s = '')
and (res.LastName like concat('%', concat(%s, '%')) or %s = '')
and (res.Room like concat('%', concat(%s, '%')) or %s = '')
and (res.CODE = %s or %s = '')
and (
        case 
            when (%s <> '' and %s <> '') then
            ((res.CheckIn >= %s and res.Checkout <= %s) or
            (res.CheckIn <= %s and res.Checkout >= %s) or
            (res.CheckIn <= %s and res.Checkout >= %s))
            else 1=1
        end
            
    )
order by res.CheckIn;
                   """, conn, params=(f_name, f_name, l_name, l_name, code, code, res_code, res_code, s_date, e_date, s_date, e_date, s_date, s_date, e_date, e_date))    
    result.index = result.index + 1
    print(result)
    conn.commit()





# view revenue details
def fr5(conn):

    print("\nHere are the revenue details for the current calendar year: \n")

    query = """
with recursive dateSeries as (
    select curdate() - interval dayofyear(curdate()) - 1 day as revenueDate
    union all
    select revenueDate + interval 1 day
    from dateSeries
    where revenueDate + interval 1 day <= last_day('2025-12-01')
),
dailyRevenue as (
    select
        res.Room,
        r.basePrice,
        d.revenueDate,
        month(d.revenueDate) as revenueMonth,
        round(case
            when weekday(d.RevenueDate) < 5 then r.basePrice
            else r.basePrice * 1.1
        end) as dailyRate
    from lab7_reservations res
    join dateSeries d on d.revenueDate >= res.CheckIn and d.revenueDate < res.Checkout
    join lab7_rooms r on res.Room = r.RoomCode
)
(select
    r.RoomCode,
    r.RoomName,
    round(sum(case when revenueMonth = 1 then dailyRate else 0 end)) as Jan,
    round(sum(case when revenueMonth = 2 then dailyRate else 0 end)) as Feb,
    round(sum(case when revenueMonth = 3 then dailyRate else 0 end)) as Mar,
    round(sum(case when revenueMonth = 4 then dailyRate else 0 end)) as Apr,
    round(sum(case when revenueMonth = 5 then dailyRate else 0 end)) as May,
    round(sum(case when revenueMonth = 6 then dailyRate else 0 end)) as Jun,
    round(sum(case when revenueMonth = 7 then dailyRate else 0 end)) as Jul,
    round(sum(case when revenueMonth = 8 then dailyRate else 0 end)) as Aug,
    round(sum(case when revenueMonth = 9 then dailyRate else 0 end)) as Sep,
    round(sum(case when revenueMonth = 10 then dailyRate else 0 end)) as Oct,
    round(sum(case when revenueMonth = 11 then dailyRate else 0 end)) as Nov,
    round(sum(case when revenueMonth = 12 then dailyRate else 0 end)) as Decm,
    round(sum(dailyRate)) as totalRevenue
from lab7_rooms r
left join dailyRevenue dr on r.RoomCode = dr.Room
group by r.RoomCode, r.RoomName)

union all

(select
    'TOTAL' as RoomCode,
    '' as RoomName,
    round(sum(case when revenueMonth = 1 then dailyRate else 0 end)) as Jan,
    round(sum(case when revenueMonth = 2 then dailyRate else 0 end)) as Feb,
    round(sum(case when revenueMonth = 3 then dailyRate else 0 end)) as Mar,
    round(sum(case when revenueMonth = 4 then dailyRate else 0 end)) as Apr,
    round(sum(case when revenueMonth = 5 then dailyRate else 0 end)) as May,
    round(sum(case when revenueMonth = 6 then dailyRate else 0 end)) as Jun,
    round(sum(case when revenueMonth = 7 then dailyRate else 0 end)) as Jul,
    round(sum(case when revenueMonth = 8 then dailyRate else 0 end)) as Aug,
    round(sum(case when revenueMonth = 9 then dailyRate else 0 end)) as Sep,
    round(sum(case when revenueMonth = 10 then dailyRate else 0 end)) as Oct,
    round(sum(case when revenueMonth = 11 then dailyRate else 0 end)) as Nov,
    round(sum(case when revenueMonth = 12 then dailyRate else 0 end)) as Decm,
    round(sum(dailyRate)) as totalRevenue
from dailyRevenue);             
                 """
    
    df = pd.read_sql(query, conn)
    df.index = df.index + 1
    print(df)





def menu(conn):
    print("""
        1. View Popular Rooms
        2. Reserve a Room
        3. Cancel a Reservation
        4. View Reservation Information
        5. View Revenue Details
    """)
    num = input("Please input the number corresponding to the service you would like to use: ").strip()
    if (num == '1'):
        fr1(conn)
    elif (num == '2'):
        fr2(conn)
    elif (num == '3'):
        fr3(conn)
    elif (num == '4'):
        fr4(conn)
    elif (num == '5'):
        fr5(conn)
    else:
        print("We're sorry, but the number you have entered does not correspond to any of the menu options. ")









def main():
    conn = connect()
    if not conn:
        print("Unable to connect to the database. Aborting.")
        return
    
    print("Welcome to the Cuties Inn room reservation system! Here are the menu options:")
    while True:
        menu(conn)
        quit = input("Would you like to continue your session? [Y/N] ")
        if quit.strip()[0] == 'N' or quit.strip()[0] == 'n':
            print("Thank you for using the Cuties Inn room reservation system! Have a fantabulous day!")
            conn.close()
            break






if __name__ == '__main__':
    main()