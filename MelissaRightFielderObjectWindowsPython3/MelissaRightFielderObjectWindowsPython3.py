"""
RightFielder Object will identify, parse and reorganize input data into usable data types,
assuring that even the most inconsistent data entry will be properly validated and stored.

High-level flow of this sample:
  1. SETUP     - create an mdRightFielder instance, hand it the license string and the
                 path to the data files, then InitializeDataFiles() (one time).
  2. INPUT     - feed one free-form contact string in.
  3. PROCESS   - Parse() splits the string into typed fields.
  4. READ      - pull the sorted fields back out with the Get* getters
                 (GetAddress, GetCity, GetState, GetPostalCode, ...).
  5. INTERPRET - GetResults() returns comma-separated result codes describing what the
                 object did/found; each code has a human description.

The pieces in this file map onto that flow:
  - run_as_console / parse_arguments : console harness (argument parsing + the interactive loop).
  - RightFielderObject               : thin wrapper around mdRightFielder that owns setup + the call sequence.
  - DataContainer                    : plain holder for one record's input and output.

Where mdRightFielder comes from:
  The mdRightFielder class lives in mdRightFielder_pythoncode.py, a generated Python wrapper over
  mdRightFielder.dll that the accompanying MelissaRightFielderObjectWindowsPython3.ps1 script
  downloads on every run.

Reference:
  Quickstart    : https://docs.melissa.com/on-premise-api/rightfielder-object/rightfielder-object-quickstart.html
  Release notes : https://releasenotes.melissa.com/on-premise-api/rightfielder-object/
  Result codes  : https://docs.melissa.com/on-premise-api/rightfielder-object/result-codes.html
"""

import mdRightFielder_pythoncode
import os
import sys
import json


class DataContainer:
    """Data holder for a single record: carries the input string in and the result codes out."""
    def __init__(self, input="", result_codes=[]):

        # Input: the free-form contact string to parse.
        self.input = input

        # Output: comma-separated result codes from GetResults().
        self.result_codes = result_codes

class RightFielderObject:
    """
    Wrapper that owns a single Melissa Right Fielder Object instance and encapsulates the
    two things every Melissa object needs: one-time setup (license + data files) and the
    per-record processing sequence. Reuse one instance across many inputs; do NOT
    re-initialize per input.
    """
    def __init__(self, license, data_path):
        """
        Perform the mandatory one-time setup, in this required order:
          1. SetLicenseString            - authorize the object.
          2. SetPathToRightFielderFiles  - tell it where the data files live.
          3. InitializeDataFiles         - load the data into memory.

        Args:
            license: The Melissa license string used to authorize the object.
            data_path: Path to the folder containing the Right Fielder Object data files.
        """
        # Set license string and set path to data files
        # The underlying Melissa Right Fielder Object instance.
        self.md_right_fielder_obj = mdRightFielder_pythoncode.mdRightFielder()
        self.md_right_fielder_obj.SetLicenseString(license)
        # Path to the Right Fielder Object data files.
        self.data_path = data_path

        # Point the object at the Right Fielder Object data files.
        self.md_right_fielder_obj.SetPathToRightFielderFiles(data_path)

        # Load the data files. The returned ProgramStatus reports whether initialization succeeded.
        # If you see a different date than expected, check your license string and either download the new data files
        # or use the Melissa Updater program to update your data files.
        p_status = self.md_right_fielder_obj.InitializeDataFiles()

        # If an issue occurred, please investigate the common causes.
        # Common causes: an invalid/expired license, or missing/wrong-path data files.
        if (p_status != mdRightFielder_pythoncode.ProgramStatus.NoError):
            print("Failed to Initialize Object.")
            print(p_status)
            return

        # Diagnostic information, handy for confirming the object loaded the data you expect:

        # Build date of the data files
        print(f"                     DataBase Date: {self.md_right_fielder_obj.GetDatabaseDate()}")

        # When the license stops working
        print(f"                   Expiration Date: {self.md_right_fielder_obj.GetLicenseExpirationDate()}")

        # This number should match with the file properties of the Melissa Object binary file.
        # If TEST appears with the build number, there may be a license key issue.
        print(f"                    Object Version: {self.md_right_fielder_obj.GetBuildNumber()}\n")


    def execute_object_and_result_codes(self, data):
        """
        Run the full Right Fielder Object processing sequence for one input string and
        capture its result codes. This is the canonical per-record call pattern to copy
        into your own application:
          Parse -> GetResults

        Args:
            data: The record to process; its free-form input string is read as input.

        Returns:
            A DataContainer carrying the same input plus this run's result codes.
        """
        # Optional: register a custom field pattern (e.g. a Social Security Number) so the
        # object recognizes and extracts it. Uncomment the SetUserPattern call to use one.
        # self.md_right_fielder_obj.SetUserPattern("SSN", "[0-9]{3}-[0-9]{2}-[0-9]{4}")

        # Split the free-form input into typed fields
        self.md_right_fielder_obj.Parse(data.input)
        # Collect the result codes for this run
        # ResultsCodes explain any issues Right Fielder Object has with the object.
        # List of result codes for Right Fielder Object
        # https://docs.melissa.com/on-premise-api/rightfielder-object/result-codes.html
        result_codes = self.md_right_fielder_obj.GetResults()

        return DataContainer(data.input, result_codes)


def parse_arguments():
    """
    Read the supported command-line options and return them as a (license, test_input,
    data_path) tuple.

    Recognized flags (each followed by its value, e.g. "--rfinput \"John Smith 22382 Avenida Empresa\""):
      --license / -l   : the Melissa license string
      --rfinput / -p   : a free-form contact string to test in one-shot mode
      --dataPath / -d  : path to the Right Fielder Object data files

    Returns:
        A (license, test_input, data_path) tuple, each entry empty when its flag
        was not supplied.
    """
    license, test_input, data_path = "", "", ""

    args = sys.argv
    index = 0
    for arg in args:

        if (arg == "--license") or (arg == "-l"):
            if (args[index+1] != None):
                license = args[index+1]
        if (arg == "--rfinput") or (arg == "-p"):
            if (args[index+1] != None):
                test_input = args[index+1]
        if (arg == "--dataPath") or (arg == "-d"):
            if (args[index+1] != None):
                data_path = args[index+1]
        index += 1

    return (license, test_input, data_path)

def run_as_console(license, test_input, data_path):
    """
    Set up the Right Fielder Object once, then drive the input -> process -> output cycle.

    In interactive mode (no --rfinput) it loops, asking for a new string each pass until the
    user answers "N". In one-shot mode (--rfinput supplied) it runs a single pass and exits.

    Args:
        license: The Melissa license string used to initialize the object.
        test_input: A free-form string to parse in one-shot mode; if empty, the program
            prompts interactively.
        data_path: Path to the Right Fielder Object data files.
    """
    print("\n\n=========== WELCOME TO MELISSA RIGHT FIELDER OBJECT WINDOWS PYTHON3 ===========\n")

    # Construct the wrapper. This is where the object is licensed, pointed at the data
    # files, and initialized (see the RightFielderObject constructor above).
    right_fielder_object = RightFielderObject(license, data_path)

    should_continue_running = True

    # Gate the program on a successful initialization. If the data files could not be
    # loaded (bad/expired license, missing or wrong-path data files, ...),
    # GetInitializeErrorString() returns the reason instead of "No Error" and we skip
    # the processing loop entirely.
    if right_fielder_object.md_right_fielder_obj.GetInitializeErrorString() != "No Error":
      should_continue_running = False

    while should_continue_running:
        if test_input == None or test_input == "":
          # Interactive mode: prompt the user for a free-form contact string.
          print("\nFill in each value to see the Right Fielder Object results")
          rf_input = str(input("Right Fielder Input: "))
        else:
          # One-shot mode: use the string passed on the command line.
          rf_input = test_input

        # Holder for this pass's input and result codes.
        data = DataContainer(rf_input)

        # Print user input
        print("\n=================================== INPUTS ====================================\n")
        print(f"\t       Right Fielder Input: {rf_input}")

        # Execute Right Fielder Object
        # Runs the Parse and returns the result codes.
        data_container = right_fielder_object.execute_object_and_result_codes(data)

        # Print output
        # Each Get* getter below returns one field the object pulled out of the input
        # string. These read directly from the mdRightFielder instance, which still holds
        # the results from the Execute call above. (Many more getters are available - see
        # the commented lines for the full set.)
        print("\n=================================== OUTPUT ====================================\n")
        print("\n\tRight Fielder Object Information:")

        # print(f"\t   Right Fielder Input: {dataContainer.Input}")
        print(f"\t        Address Line 1: {right_fielder_object.md_right_fielder_obj.GetAddress()}")
        print(f"\t        Address Line 2: {right_fielder_object.md_right_fielder_obj.GetAddress2()}")
        print(f"\t        Address Line 3: {right_fielder_object.md_right_fielder_obj.GetAddress3()}")
        print(f"\t                  City: {right_fielder_object.md_right_fielder_obj.GetCity()}")
        print(f"\t                 State: {right_fielder_object.md_right_fielder_obj.GetState()}")
        print(f"\t                   Zip: {right_fielder_object.md_right_fielder_obj.GetPostalCode()}")
        print(f"\t          Result Codes: {data_container.result_codes}")

        # right_fielder_object.md_right_fielder_obj.GetFullNameNext()
        # print(f"\t              FullName: {right_fielder_object.md_right_fielder_obj.GetFullName()}")
        # right_fielder_object.md_right_fielder_obj.GetDepartmentNext()
        # print(f"\t            Department: {right_fielder_object.md_right_fielder_obj.GetDepartment()}")
        # right_fielder_object.md_right_fielder_obj.GetCompanyNext()
        # print(f"\t               Company: {right_fielder_object.md_right_fielder_obj.GetCompany()}")
        # print(f"\t               Country: {right_fielder_object.md_right_fielder_obj.GetCountry()}")
        # print(f"\t              LastLine: {right_fielder_object.md_right_fielder_obj.GetLastLine()}")
        # right_fielder_object.md_right_fielder_obj.GetPhoneNext()
        # print(f"\t                 Phone: {right_fielder_object.md_right_fielder_obj.GetPhone()}")
        # right_fielder_object.md_right_fielder_obj.GetPhoneTypeNext()
        # print(f"\t             PhoneType: {right_fielder_object.md_right_fielder_obj.GetPhoneType()}")
        # right_fielder_object.md_right_fielder_obj.GetEmailNext()
        # print(f"\t                 Email: {right_fielder_object.md_right_fielder_obj.GetEmail()}")
        # right_fielder_object.md_right_fielder_obj.GetURLNext()
        # print(f"\t                   Url: {right_fielder_object.md_right_fielder_obj.GetURL()}")
        # right_fielder_object.md_right_fielder_obj.GetUserFieldNext("SSN")
        # print(f"\t             UserField: {right_fielder_object.md_right_fielder_obj.GetUserField('SSN')}")
        # right_fielder_object.md_right_fielder_obj.GetUnrecognizedNext()
        # print(f"\t          Unrecognized: {right_fielder_object.md_right_fielder_obj.GetUnrecognized()}")



        # Result codes come back as a single comma-separated string (e.g. "RA01,RF01").
        # Split it and ask the object for a readable description of each code.
        # ResultCodeDescriptionLong requests the long-form text; a short form is also
        # available via ResultCodeDescriptionShort
        rs = data_container.result_codes.split(',')
        for r in rs:
            print(f"        {r}: {right_fielder_object.md_right_fielder_obj.GetResultCodeDescription(r, mdRightFielder_pythoncode.ResultCdDescOpt.ResultCodeDescriptionLong)}")


        is_valid = False

        # In one-shot mode there is nothing more to do after a single pass: mark the
        # input handled and stop the outer loop.
        if not (test_input == None or test_input == ""):
            is_valid = True
            should_continue_running = False
        # Interactive mode: ask whether to process another string. Keep prompting until we
        # get a valid Y/N. "N" ends the program; "Y" falls through to another pass.
        while not is_valid:

            test_another_response = input(str("\nTest Right Fielder Again? (Y/N)\n"))


            if not (test_another_response == None or test_another_response == ""):
                test_another_response = test_another_response.lower()
            if test_another_response == "y":
                is_valid = True

            elif test_another_response == "n":
                is_valid = True
                should_continue_running = False
            else:

              print("Invalid Response, please respond 'Y' or 'N'")

    print("\n=================== THANK YOU FOR USING MELISSA PYTHON3 OBJECT ================\n")



# ---------------------------- MAIN STARTS HERE ----------------------------

# Read the optional command-line arguments, then hand control to run_as_console, which
# performs the actual Right Fielder Object setup and processing.
license, test_input, data_path = parse_arguments()

run_as_console(license, test_input, data_path)