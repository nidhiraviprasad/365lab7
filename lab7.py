import getpass
import mysql.connector

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
        confirmation = input("Are you sure you would like to cancel the above reservation? [Y to confirm; any other key to cancel]" ).strip()
        if (confirmation == 'Y' or confirmation == 'y'):
            cursor.execute("""
DELETE
from lab7_reservations
WHERE CODE = %s
                   """, [code])
        else:
            print("Your reservation was not cancelled.")
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