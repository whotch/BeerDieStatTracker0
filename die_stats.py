############################################
# die_stats.py
# Phase 1 of Beer Die Stat Tracker
# Created by William Hotch
# November 28 2023
############################################

import sqlite3

######################
# CUSTOM OBJECTS 
######################

# Move object
class Move:

    # SELF
    def __init__(self, player_id, player_name, action):
        self.player_id = player_id
        self.player_name = player_name
        self.action = action

    # GETTERS
    def get_player_id(self):
        return self.player_id
    
    def get_player_name(self):
        return self.player_name

    def get_action(self):
        return self.action

    #SETTERS
    def set_player_id(self, id):
        self.player_id = id

    def set_player_name(self, name):
        self.player_name = name

    def set_action(self, act):
        self.action = act

    # PRINT
    def __str__(self):
        return f"Player {self.player_name} performed action: {self.action}"

# Game object
class Game:

    # SELF
    def __init__(self):
        self.plays = []
        self.score = [0, 0]
        self.player_array = []

    # GETTERS
    def get_plays(self):
        return self.plays

    def get_score(self):
        return self.score

    def get_player_array(self):
        return self.player_array

    def get_winning_team(self):
        if self.score[0] > self.score[1]:
            return 1
        elif self.score[0] < self.score[1]:
            return 2
        else:
            raise GameCannotEndTied("Cannot end game on a tie!")

    # SETTERS
    def add_move(self, move):
        self.plays.append(move)

    def undo_move(self):
        return self.plays.pop()

    def update_player_array(self, value, pl_array):
        if value not in pl_array:
            self.player_array.append(value)
        else: raise PlayerAlreadyInGameError("Player is already in the game.")

    def update_score(self, team, amt):
        self.score[team - 1] += amt

    # PRINT
    def __str__(self):
        return (
            f"Plays: {', '.join(str(move) for move in self.plays)}\n"
            f"Score: {self.score}\n"
        )


######################
# CUSTOM ERRORS 
######################

# Raised when user adds a player to a game that is already in game
class PlayerAlreadyInGameError(Exception):
    pass

# Raised when user selects game player not 1 thru 4
class InvalidPlayerNumberError(Exception):
    pass

# Raised when user selects a Player ID that does not exist
class PlayerNotFoundError(Exception):
    pass

# Raised when user selects an event that does not exist
class InvalidEventError(Exception):
    pass

# Raised when user ends a game that is tied
class GameCannotEndTied(Exception):
    pass


######################
# DATABASE CONNECTION
######################

# Create a connection to the SQLite database
def connect_to_database(database_name):

    connection = sqlite3.connect(database_name)
    return connection

# Create a table if it doesn't exist
def create_table(connection):
    
    create_table_func = '''
        CREATE TABLE IF NOT EXISTS Players (
            id              INTEGER PRIMARY KEY,
            name            TEXT,
            airballs        INTEGER DEFAULT (0),
            too_shorts      INTEGER DEFAULT (0),
            table_hits      INTEGER DEFAULT 0,
            cup_hits        INTEGER DEFAULT 0,
            pts1            INTEGER DEFAULT 0,
            pts2            INTEGER DEFAULT 0,
            sinks           INTEGER DEFAULT 0,
            catch1s         INTEGER DEFAULT 0,
            catch2s         INTEGER DEFAULT 0,
            drop1s          INTEGER DEFAULT 0,
            drop2s          INTEGER DEFAULT 0,
            fifa_fails      INTEGER DEFAULT 0,
            fifa_succs      INTEGER DEFAULT 0,
            tosses          INTEGER DEFAULT 0,
            tosses_defended INTEGER DEFAULT 0,
            wins            INTEGER DEFAULT 0,
            losses          INTEGER DEFAULT 0,
            games           INTEGER DEFAULT 0
        )
    '''

    cursor = connection.cursor()
    cursor.execute(create_table_func)
    connection.commit()


######################
# CONSOLE PRINTERS
######################

# Print all existing players alongside their ID
def display_players(connection, arr):

    cursor = connection.cursor()

    # Construct a parameterized query to retrieve players excluding those in arr
    query = "SELECT id, name FROM Players WHERE id NOT IN ({}) ORDER BY id"
    formatted_ids = ', '.join(map(str, arr))
    cursor.execute(query.format(formatted_ids))

    # Fetch the result
    players = cursor.fetchall()

    # Print the players
    print("Players:")
    for player in players:
        print(f"ID: {player[0]}, Name: {player[1]}")

# Print the events
def display_events(connection):

    cursor = connection.cursor()

    query = '''
        SELECT event
        FROM ColumnInformation
        ORDER BY id
        LIMIT 14 OFFSET 2;
    '''
    cursor.execute(query)

    # Fetch the result
    values = cursor.fetchall()

    # Print the values
    events = [value[0] for value in values]
    for event in events:
        print(event)

    # Return list of events
    events_lower = [event.lower() for event in events]
    return events_lower

# Retrieve player names by IDs in the order of appearance
def print_game_players(connection, game):

    cursor = connection.cursor()

    query = "SELECT name FROM Players WHERE id IN ({}) ORDER BY instr(?, id)"
    formatted_ids = ', '.join(map(str, game.get_player_array()))
    cursor.execute(query.format(formatted_ids), (formatted_ids,))

    # Fetch the result
    player_names = cursor.fetchall()

    # Print the player names with enumeration
    print("Player Names:")
    for index, player_name in enumerate(player_names, start = 1):
        print(f"{index}. {player_name[0]}")


######################
# GAME FUNCTIONS
######################

# Insert a new player into the Players table
def add_player(connection, name):

    add_player_func = '''
        INSERT INTO Players (name)
        VALUES (?)
    '''

    cursor = connection.cursor()
    cursor.execute(add_player_func, (name,))
    connection.commit()

# Delete a player from the Players table
def delete_player(connection, player_id):
    
    # Validate user input
    does_player_id_exist(connection, player_id)
    
    delete_func = "DELETE FROM Players WHERE id = ?"

    cursor = connection.cursor()
    cursor.execute(delete_func, (player_id,))
    connection.commit()

# Update a stat in the Players table
def update_stat(connection, id, event, amt):

    # Get column_name from user input
    stat = get_column_name_by_event(connection, event)

    if stat:
        update_func = f"UPDATE Players SET {stat} = {stat} + {amt} WHERE id = ?"

        cursor = connection.cursor()
        cursor.execute(update_func, (id,))
        connection.commit()
    else:
        print(f"{event} could not be found.")

# Update a stat in the Players table
def update_w_l(connection, id, outcome):

    # Get column name
    if outcome == 'w':
        column = "wins"
    else:
        column = "losses"

    update_func = f"UPDATE Players SET {column} = {column} + 1 WHERE id = ?"

    cursor = connection.cursor()
    cursor.execute(update_func, (id,))
    connection.commit()

def update_totals(connection, id):

    # Add one game played
    update_games_func = f"UPDATE Players SET games = wins + losses WHERE id = ?"

    # Update tosses totals
    update_off_totals_func = f"UPDATE Players SET tosses = airballs + too_shorts + table_hits + cup_hits + pts1 + pts2 + sinks WHERE id = ?;"

    # Update tosses defended totals
    update_def_totals_func = f"UPDATE Players SET tosses_defended = catch1s + catch2s + drop1s + drop2s + fifa_fails + fifa_succs WHERE id = ?;"

    # Execute and commit all three update queries
    cursor = connection.cursor()
    cursor.execute(update_games_func, (id,))
    cursor.execute(update_off_totals_func, (id,))
    cursor.execute(update_def_totals_func, (id,))
    connection.commit()

# View the stats of an existing player
def view_player_stats(connection, player_id):

    # Validate user input
    does_player_id_exist(connection, player_id)
    
    cursor = connection.cursor()

    player_query = f"SELECT * FROM Players WHERE id = {player_id}"
    cursor.execute(player_query)
    player_data = cursor.fetchone()

    # Iterate over each "description" column in ColumnInformation
    desc_query = "SELECT column_name, description FROM ColumnInformation WHERE id > 2"
    cursor.execute(desc_query)
    descriptions = cursor.fetchall()

    # Print the player's name
    print(f"Player Name: {player_data[1]}")

    # Print each "description" column with the corresponding value
    for column_name, description in descriptions:
        # Find the index of the column by directly comparing column names
        try:
            index = [desc[0] for desc in descriptions].index(column_name)
        except ValueError:
            print(f"{column_name} not found in descriptions")

        if index is not None:
            # The value is in the index two to the right from the column in the player_data tuple
            value = player_data[index + 2]
            print(f"{description}: {value}")
        else:
            print(f"Column '{column_name}' not found in result set description.")

# Determine points scored by an event
def determine_points(event):
    
    # check for scoring plays
    if event.lower() == "1 pointer":
        points = 1
    elif event.lower() == "2 pointer":
        points = 2
    elif event.lower() == "sink":
        points = 3

    # FIFA scoring
    elif event.lower() == "successful fifa":
        points = 1

    # no points scored
    else:
        points = 0

    return points


######################
# GETTERS
######################

# Get stat column from user-friendly event name
def get_column_name_by_event(connection, event):

    cursor = connection.cursor()
    
    # Use a parameterized query to avoid SQL injection
    query = "SELECT column_name FROM ColumnInformation WHERE event COLLATE NOCASE = ?;"
    cursor.execute(query, (event,))
    
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        return None

# Retrieve player name by IDs
def get_name_by_id(connection, player_id):

    cursor = connection.cursor()

    query = "SELECT name FROM Players WHERE id = ?"
    cursor.execute(query, (player_id,))

    result = cursor.fetchone()

    if result:
        return result[0]
    else:
        return None

# Retrieve team number by player ID
def get_team_by_id(player_id, player_array):

    try:
        index = player_array.index(player_id)
        if index in (0, 1):
            return 1
        else:
            return 2
    except ValueError:
        # Handle the case where player_id is not in player_array
        return None

# Get available players that can be selected for a game
def get_available_players(connection, arr):

    cursor = connection.cursor()

    # Construct a parameterized query to retrieve players excluding those in arr
    query = "SELECT id, name FROM Players WHERE id NOT IN ({}) ORDER BY id"
    formatted_ids = ', '.join(map(str, arr))
    cursor.execute(query.format(formatted_ids))

    # Fetch the result
    return cursor.fetchall()

# Get the number of existing players
def get_num_players(connection, arr):
    cursor = connection.cursor()

    # Construct a parameterized query to retrieve players excluding those in arr
    query = "SELECT COUNT(*) FROM Players WHERE id NOT IN ({})"
    formatted_ids = ', '.join(map(str, arr))
    cursor.execute(query.format(formatted_ids))

    # Fetch the result
    num_players = cursor.fetchone()[0]
    return num_players


######################
# VALIDATORS
######################

# Validates that selected Player ID exists
def does_player_id_exist(connection, player_id):

    check_query = "SELECT 1 FROM Players WHERE id = ?"
    cursor = connection.cursor()
    cursor.execute(check_query, (player_id,))
    exists = cursor.fetchone()
    
    if not exists:
        raise PlayerNotFoundError(f"Player with ID {player_id} not found in the Players table.")


# Get a valid player ID from the user
def get_valid_player_id(connection, game, team):

    while True:
        display_players(connection, game.get_player_array())
        curr_player_index = len(game.get_player_array())
        user_input = input(f"Type the number of Player {curr_player_index + 1} (Team {team}): ")
        
        try:
            player_number = int(user_input)

            # Check if the entered player number is an available option
            available_players = [player[0] for player in get_available_players(connection, game.get_player_array())]
            if player_number not in available_players:
                raise PlayerNotFoundError(f"Player with ID {player_number} is not available.")

            # Update player_array if valid Player ID
            game.update_player_array(player_number, game.get_player_array())
            break
        
        except PlayerAlreadyInGameError as e:
            print(e)
        except ValueError:
            print("Invalid input. Please type a number.")
        except PlayerNotFoundError as e:
            print(e)

    return player_number

# Get a valid game player (1 thru 4) from the user
def get_valid_game_player():

    while True:
        try:
            selected_player = int(input("Type the number of the player: "))
            if 1 <= selected_player <= 4:
                return selected_player
            else:
                raise InvalidPlayerNumberError("Player number must be between 1 and 4.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

# Get a valid event from the user
def get_valid_event(connection):

    while True:
        valid_events = display_events(connection)
        selected_event = input("Type the name of the action: ").lower()

        if selected_event in valid_events:
            return selected_event
        else:
            try:
                raise InvalidEventError(f"Invalid event: {selected_event}. Please try again.")
            except InvalidEventError as e:
                print(e)


######################
# GAMEPLAY
######################
def start_game(connection):

    game = Game()

    # Get players for Team 1
    get_valid_player_id(connection, game, 1)
    get_valid_player_id(connection, game, 1)

    # Get players for Team 2
    get_valid_player_id(connection, game, 2)
    get_valid_player_id(connection, game, 2)

    # Do not ever call get_valid_player_id() more than 4 times

    prompt = "Would you like to add a move (move), undo a move (undo), or end the game (gameover): "
    
    while True:
        user_input = input(prompt).lower()

        if user_input == "move":

            # Show user the unselected players
            print_game_players(connection, game)

            # Keep trying to get a valid answer
            while True:
                try:
                    player_number = get_valid_game_player()
                    break 
                except InvalidPlayerNumberError as e:
                    print(f"Error: {e}")

            # Determine the team of the player that performed the action
            p_arr = game.get_player_array()
            curr_player_id = p_arr[player_number - 1]
            if 1 <= player_number <= 2:
                team_number = 1
            else:
                team_number = 2

            # Have user select event 
            selected_event = get_valid_event(connection)
            points_scored = determine_points(selected_event.lower())

            # 'Do' the move
            new_move = Move(curr_player_id, get_name_by_id(connection, curr_player_id), selected_event)
            print(new_move)
            game.add_move(new_move)
            game.update_score(team_number, points_scored)
            print(game, '\n')

        elif user_input == "undo":

            if game.get_plays():
                undid = game.undo_move()

                undo_player = undid.get_player_id()
                undo_team = get_team_by_id(undo_player, game.get_player_array())
                undo_event = undid.get_action()
                undo_points = -determine_points(undo_event.lower())

                game.update_score(undo_team, undo_points)

                print("Undone move: ", undid)
                print(game, '\n')
            
            else:
                print("There are no moves to undo!")

        elif user_input == "gameover":

            # Make sure game is not tied
            try:
                winning_team = game.get_winning_team()

                # Confirm with user because gameover is irreversible
                new_input = input('''Are you sure you want to end the game? Gameover is irreverisble.
Press any key to end game. (If you want to continue the game, type 'cancel'.)''')
                if new_input != "cancel":

                    # When game is over, update player stats by iterating thru all plays in game
                    for play in game.get_plays():
                        curr_player_id = play.get_player_id()
                        curr_event = play.get_action()

                        # Update individual statistics
                        update_stat(connection, curr_player_id, curr_event, 1)

                    # Update wins and losses
                    # If Team 1 wins                    
                    if winning_team == 1:
                        update_w_l(connection, game.get_player_array()[0], 'w')
                        update_w_l(connection, game.get_player_array()[1], 'w')

                        update_w_l(connection, game.get_player_array()[2], 'l')
                        update_w_l(connection, game.get_player_array()[3], 'l')
                    
                    # If Team 2 wins
                    else:
                        update_w_l(connection, game.get_player_array()[0], 'l')
                        update_w_l(connection, game.get_player_array()[1], 'l')

                        update_w_l(connection, game.get_player_array()[2], 'w')
                        update_w_l(connection, game.get_player_array()[3], 'w')

                    # Update totals (games, tosses, tosses defended)
                    for player_id in game.get_player_array():
                        update_totals(connection, player_id)

                    print("Gameover\n")
                    break

            except GameCannotEndTied as e:
                print(f"Error: {e}")

            
        else:
            print(f"{user_input} is not a valid command. Please type move, undo, or gameover.")


######################
# MAIN
######################

def main():

    # Specify the name of the SQLite database
    database_name = 'Stats.db'

    # Connect to the database
    connection = connect_to_database(database_name)

    # Create the Players table if it doesn't exist
    create_table(connection)

    # Take command line input from user

    print("\nWelcome to the first, only, and best Beer Die Stat Tracker! ")

    text = '''Type the action you would like to perform:
            Add a player (add)
            Delete a player (delete)
            View existing players (view)
            View player stats (stats)
            Start a game (game)
            Quit (quit)
'''

    while True:
        # Take user input
        user_input = input(text).lower()
        
        # Quit the program
        if user_input.lower() == 'quit':
            print("Exiting the program.")
            break

        # Add a player
        elif user_input.lower() == 'add':
            new_name = input("Enter the name (or type 'cancel'): ")
            if new_name.lower() != "cancel":
                add_player(connection, new_name)
                print("Added player", new_name)
                display_players(connection, [])
        
        # Delete a player
        elif user_input.lower() == 'delete':
            display_players(connection, [])

            # Validate user input (must be integer and a valid Player ID)
            while True:
                user_input = input("Type the number of the player you want to delete (or type 'cancel'): ")
                if user_input.lower() == "cancel":
                    break

                try:    
                    player_id_to_delete = int(user_input)
                    print(f"Deleted Player {player_id_to_delete} {get_name_by_id(connection, player_id_to_delete)}")
                    delete_player(connection, player_id_to_delete)
                    display_players(connection, [])
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid player ID (an integer).")
                except PlayerNotFoundError as e:
                    print(f"Error: {e}")

        # View all existing players
        elif user_input.lower() == 'view':
            display_players(connection, [])

        # View stats of an existing player
        elif user_input.lower() == 'stats':
            display_players(connection, [])
            while True:
                curr_player = input("Type the number of the player you want to view the stats of (or type 'cancel'): ")
                if curr_player.lower() == "cancel":
                    break

                try:
                    curr_player_id = int(curr_player)
                    view_player_stats(connection, curr_player_id)
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid player ID (an integer).")
                except PlayerNotFoundError as e:
                    print(f"Error: {e}")
                
        # Start a game
        elif user_input.lower() == 'game':
            if get_num_players(connection, []) < 4:
                print("There are not enough players exist to start a game! Please add players before starting a game.")
            
            else: start_game(connection)
        
        # Invalid option selected
        else:
            print(f"{user_input.lower()} is not an option.")

        print(" ")

    # Close the database connection
    connection.close()

if __name__ == "__main__":
    main()