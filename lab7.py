import getpass
import mysql.connector
import datetime
from decimal import Decimal

def connect():
    db_password = getpass.getpass()
    conn = mysql.connector.connect(user='nravipra', password=db_password,
                               host='mysql.labthreesixfive.com',
                               database='nravipra')
    return conn


# view popular rooms
def fr1(conn):
    print("Here are our rooms, sorted by popularity: ")
    cursor = conn.cursor()
    cursor.execute("""
                   
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
                   
                   """)
    result = cursor.fetchall()
    print(result)
    cursor.close()


# make a reservation
def fr2(conn):
    print("Please enter the following information to make your reservation: ")
    f_name = input("First name: ").strip()
    l_name = input("Last name: ").strip()
    code = input("Room code (enter 'Any' if you have no preference): ").strip()
    bed = input("Bed type (enter 'Any' if you have no preference): ").strip()
    checkin = input("Check in date (MM/DD/YYYY): ").strip()
    checkout = input("Check out date (MM/DD/YYYY): ").strip()
    children = input("Number of children: ").strip()
    adults = input("Number of adults: ").strip()

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

    cursor = conn.cursor()
    cursor.execute("""
select *
from lab7_rooms r
where (r.RoomCode = %s or %s = 'Any' or %s = '')
and (r.bedType = %s or %s = 'Any' or %s = '')
and r.maxOcc >= %s
and ( 
    select count(*)
    from lab7_reservations res
    where (r.RoomCode = res.Room or %s = 'Any' or %s = '')
    and (
        (res.CheckIn >= %s and res.Checkout <= %s) or
        (res.CheckIn <= %s and res.Checkout >= %s) or
        (res.CheckIn <= %s and res.Checkout >= %s)
        )
    ) = 0;
                   """, [code, code, code, bed, bed, bed, str(numOccupants), code, code, ci, co, co, co, ci, ci])
    
    room_details = cursor.fetchall()
    if (room_details):
        for i in range(len(room_details)):
            print(f"{i + 1}: {room_details[i]}")
        room = input("Which of the following rooms would you like to book? Please enter the option number: ")
        while not room.isnumeric() or int(room) > len(room_details) or int(room) < 1:
            room = input("Invalid room selection. Please select from the given options: ")
        room = int(room) - 1

        basePrice = float(room_details[room][5])

        cursor.execute("""
select max(CODE) from lab7_reservations;
                       """)
        result = cursor.fetchall()
        if result:
            newCode = str(int(result[0][0]) + 1)
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
        costOfStay = "Decimal('" + str(costOfStay) + "')"

        cursor.execute("""
insert into lab7_reservations 
(CODE, Room, CheckIn, Checkout, Rate, LastName, FirstName, Adults, Kids)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                       """, [newCode, room_details[room][0], ci, co, costOfStay, l_name, f_name, adults, children])
        
        
        print(f"\nConfirmed! {f_name} {l_name} has booked room {room_details[room][0]}: {room_details[room][1]}." +
              f"\nBed type: {room_details[room][3]}" +
              f"\nDates: {ci} to {co}" +
              f"\nOccupants: {adults} adults and {children} children" +
              f"\nTotal cost: {costOfStay}" + 
              f"\nConfirmation code: {newCode}\n")
        
        


            
    else:
        print("womp womp")




        


# cancel a reservation
def fr3(conn):
    code = input("Please enter the reservation code for the reservation you would like to cancel: ").strip()
    cursor = conn.cursor()
    cursor.execute("""
SELECT *
from lab7_reservations
WHERE CODE = %s
                   """, [code])
    result = cursor.fetchall()
    if (result):
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
    cursor.close()


# view reservation details
def fr4(conn):
    pass


# view revenue details
def fr5(conn):
    pass



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
            print("Thank you for using the Cuties Inn room reservation system! We hope you have a great day!")
            break



if __name__ == '__main__':
    main()