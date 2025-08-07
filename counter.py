import os

# Define a file to store the counter
counter_file = 'counter.txt'

def read_counter():
    """Read the current counter value from the file, or initialize it."""
    if os.path.exists(counter_file):
        with open(counter_file, 'r') as file:
            return int(file.read())
    return 0

def write_counter(count):
    """Write the counter value to the file."""
    with open(counter_file, 'w') as file:
        file.write(str(count))

def execute_code():
    """Function that you want to keep track of."""
    # Read the current counter value
    count = read_counter()
    
    # Increment the counter
    count += 1
    
    # Execute the code
    print(f"Executing code. This is execution number {count}.")
    
    # Write the updated counter value
    write_counter(count)

# Example usage
execute_code()