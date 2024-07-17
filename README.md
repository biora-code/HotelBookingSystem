End user perspective:
1. Go to the website and see different destinations/hotels
2. Search destination details (city, dates, number of rooms, room types, etc.)
3. Get filtered hotels, prices in user selected currency
4. Select the suitable room option and continue with booking by signing up/login and
generating and downloading booking receipt OR repeat step 1.
End user features include: Register/Login/Logout/password update; create, view, update,
cancel booking;


Admin user perspective and features include:
1. Admin should be able to Login/Logout and update password for admin as well as
other users on the system.
2. Admin should be able to perform following tasks: Adding/updating/removing hotels
or prices, currencies, exchange rates, constraints and end user details
3. Admin should be able to check and set status (booked, available) of a room
4. Admin should be able to generate admin reports e.g., monthly sales, sales for each
hotel, top customers, hotels making profit, hotels in loss, etc.

Check-in date should be used to check whether it is peak-season or off-peak season.
Each room has specific features such as Wifi, mini-bar, TV, breakfast etc.
Advanced booking discount should be checked and applied from the check-in date.
Booking cancellation before 60 days of booking date does not incur cancellation charges.
Booking cancellation between 30 and 60 days of booking date will incur charges up to 40%
of booking price. Within 30 days of booking date 80% of booking price will be charged. 
Within 10 days of booking date 100% of booking price will be charged. You must implement
handling of cancellation charges and manage it properly in your database.
Each hotel has 4 types of rooms: 1. Standard room; 2. Double room; 3. Family room and 4.
Executive suite. Each hotel has 30% standard room; 40% double rooms, 20% Family rooms
and 10% Executive suite. A standard room can have 1 guest only. A double room is 20%
more price of a Standard room and can have 2 guests max. For second guest extra 10% of a
Standard room price will also be charged. Family room is 50% more price of a Standard
room and can accommodate a family of maximum 4 guests. Executive suite has 5 times the
price of a standard room and there is no extra charge for an additional guest.
Admin user should be able to set as well as check the status of a selected room i.e., what is
the current status of the room e.g., Available (i.e., room is available for booking), Booked (It
is currently booked but show the date when will it be available), Unavailable due to
maintenance.
A customer can book for maximum 20 days stay. If more than 20 days stay is required then
customer will need to make separate bookings.
