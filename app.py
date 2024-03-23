#!/usr/bin/env python
# -*- coding: utf-8 -*-

# In[9]:


# Install the required modules
import panel as pn 
import param
import os
import tempfile
import fractions
import math

#set extension
pn.extension('tabulator')
pn.extension(sizing_mode="stretch_width")
pn.extension(notifications=True)


# # Helper Functions

# In[10]:


# compute for e-prime
def compute_eprime(exponent):
    e = int(exponent) + 101
    e_prime = bin(e)[2:].zfill(8)

    return e, e_prime


# In[11]:


# convert decimal in str format to 4-bit binary
def str_to_binary(string):
    binary_list = []
        
    for char in string:
        integer = int(char)
        binary = format(integer, 'b').zfill(4)
        binary_list.append(binary)
        
    return ''.join(binary_list)


# In[12]:


# compute for combination bits
def compute_combination_bits(e_prime, msd):
    combination = ""
    exp_bin = str(e_prime)
    msd_bin = bin(int(msd))[2:].zfill(4)
        
    if int(msd) <= 7:
        combination = exp_bin[:2] + msd_bin[1:] 
    else:
        combination = "11" + exp_bin[:2] + msd_bin[-1]

    return combination


# In[13]:


# convert binary to dp bcd
def bin_to_dpbcd(string):
    a, b, c, d, e, f, g, h, i, j, k, m = map(int, string)
    
    p = int(b or (a and j) or (a and f and i))
    q = int(c or (a and k) or (a and g and i))
    r = d
    s = int((f and (not a or not i)) or (not a and e and j) or (e and i))
    t = int(g or (not a and e and k) or (a and i))
    u = h
    v = int(a or e or i)
    w = int(a or (e and i) or (not e and j))
    x = int(e or (a and i) or (not a and k))
    y = m
    
    return ''.join(map(str, [p, q, r, s, t, u, v, w, x, y]))


# In[14]:


# round decimal to nearest ties to even
def round_ties_to_even(decimal_str, remaining):
    rounded_decimal = ""
    
    # get upper and lower bound to compare with decimal
    lower = int(remaining[0]) * (10**(len(remaining)-1))
    higher = (int(remaining[0]) + 1)* (10**(len(remaining)-1))

    # round down
    if abs(int(remaining) - lower) < abs(int(remaining) - higher):
        print ("The given number is closer to the smaller number.")
        rounded_decimal = decimal_str + remaining[0]
        print(rounded_decimal)
                    
    # round up
    elif abs(int(remaining) - higher) < abs(int(remaining) - lower):
        print ("The given number is closer to the higher number.")
        rounded_decimal = decimal_str + str(int(remaining[0])+1)
        print(rounded_decimal)

    # tie
    else:
        print("The given number is equidistant from both numbers.")
        # 7th digit is even, round down
        if int(remaining[0]) % 2 == 0:
            rounded_decimal = decimal_str + remaining[0]
            print(rounded_decimal)
        # 6th digit is odd, round up
        else:
            rounded_decimal = decimal_str + str(int(remaining[0])+1)
            print(rounded_decimal)

    return rounded_decimal


# # Dashboard Set up

# In[15]:


class Converter(param.Parameterized):
    # variables
    sign = 0                  # sign bit
    msd = 0                   # most significant digit
    exp = 0                   # initial exponent - decimal jump
    e_prime_bits = 0          # e-prime in binary
    e_prime_dec = 0           # e-prime in decimal
    combo_bits = ""           # combination bits
    decimal_unnormalized = "" # unnormalized decimal    
    decimal_normalized = ""   # normalized decimal
    decimal_last6 = ""        # last 6 digits of the normalized decimal
    bcd_bits = ""             # bcd bits
    bresult = ""              # final answer in binary
    hresult = ""              # final answer in hex
    case_decimal = ""         # zero / NaN
    case_exponent = ""        # denormalized / infinity
    
    # input fields
    decimal         = pn.widgets.TextInput(name='Decimal', placeholder='Enter a number here...')
    exponent        = pn.widgets.TextInput(name='Exponent (Base-10)', placeholder='Enter exponent here...')
    rounding_method = pn.widgets.Select(name='Rounding Method', options=['Truncate', 'Round up', 'Round down', 'Round to nearest ties to even'], disabled=True)

    # buttons
    compute_btn = pn.widgets.Button(name='Compute', button_type='primary')
    

    # stylesheet for download button
    style_sheet_download = """
    .bk-btn a {
        display: inline-block;
        width: 439px !important;
        height: 34px !important;
        background-color: #AAC8A7;
        border-radius: 5px;
        cursor: pointer;
        @media (min-width: 760px) {
            width: 100% !important;
        }
    }
    """
    # Append the stylesheet
    pn.widgets.FileDownload.stylesheets.append(style_sheet_download)

    download_btn = pn.widgets.FileDownload(label='Export', button_type='primary', disabled=True)
    

    # input validation prompts
    validate_decimal_prompt     = pn.pane.HTML("<font color='red'> </font>")
    validate_exponent_prompt    = pn.pane.HTML("<font color='red'> </font>")

    # process holders 
    normalized_decimal_text     = pn.pane.HTML("<b>Normalized Decimal: ")
    exponent_text               = pn.pane.HTML("Final Exponent: ")
    e_prime_text                = pn.pane.HTML("E-Prime: ")
    sign_text                   = pn.pane.HTML("Sign Bit: ")
    combination_text            = pn.pane.HTML("Combination: ")
    exponent_continuation_text  = pn.pane.HTML("Exponent Bits: ")
    bcd_bits_text               = pn.pane.HTML("Densely Packed BCD: ")

    # result holders
    result_binary = pn.pane.HTML("Final Answer (Binary): ")
    result_hex = pn.pane.HTML("Final Answer (Hex): ")

    # styles
    style_output1 = 'text-align: left; background-color: #f0f0f0; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output2 = 'text-align: left; background-color: #cbcbf4; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output3 = 'text-align: left; background-color: #C96E86; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output3 = 'text-align: left; background-color: #C96E86; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output4 = 'text-align: left; background-color: #C1DBDA; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output5 = 'text-align: left; background-color: #D1C2D9; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output6 = 'text-align: left; background-color: #E2BFB3; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output7 = 'text-align: left; background-color: #F3E6C0; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    style_output8 = 'text-align: left; background-color: #F0D1D4; padding: 5px; border-radius: 5px; width: 100%; word-wrap: break-word;'
    
    # constructor
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sign = 0
        self.msd = 0
        self.exp = 0
        self.e_prime_bits = 0
        self.combo_bits = ""
        self.decimal_normalized = ""
        self.bcd_bits = ""
        
    # allow user to choose round method if decimal > 7 digits
    @param.depends('decimal.value', watch=True)
    def _enable_round_method(self):
        # check if input is negative
        if '-' in self.decimal.value:
            self.decimal_unnormalized = self.decimal.value.replace('-', '')
            self.sign = 1
        else:
            self.decimal_unnormalized = self.decimal.value
            self.sign = 0
            
        digit_count = len(self.decimal_unnormalized)
        
        # Check if input contains decimal point
        if '.' in self.decimal_unnormalized:
            digit_count = len(self.decimal_unnormalized.replace('.', ''))

        self.rounding_method.disabled = digit_count <= 7

    # check if input for decimal is valid
    # @param.depends('decimal.value', watch=True)
    def validate_decimal(self):
        # Check if value is empty or contains only whitespace
        if not self.decimal.value.strip():  
            self.validate_decimal_prompt.object = "<font color='red'>Field is empty. Please enter a decimal number.</font>"
            return
        
        # check if fraction
        if '/' in self.decimal.value:
            try:
                # Parse the fraction
                fraction = fractions.Fraction(self.decimal.value)
                
                # Calculate decimal value
                decimal_value = fraction.numerator / fraction.denominator
            
                # Convert decimal value to string
                self.decimal.value = str(decimal_value)
                self.validate_decimal_prompt.object = "<font color='red'> </font>"
                
            except ValueError:
                self.validate_decimal_prompt.object = "<font color='red'>Invalid input. Please enter a valid decimal number.</font>"
            except ZeroDivisionError:
                self.decimal.value = str("NaN")
                
        # check if square root
        if self.decimal.value.startswith("sqrt(") and self.decimal.value.endswith(")"):
            try:
                # Extract the expression inside sqrt
                inner_expression = self.decimal.value[5:-1]

                # Evaluate the expression inside sqrt
                sqrt_value = math.sqrt(float(inner_expression))

                # Update the input value with the square root result
                self.decimal.value = str(sqrt_value)
                self.validate_decimal_prompt.object = "<font color='red'> </font>"

            except ValueError:
                if '-' in self.decimal.value:
                    self.decimal.value = str("NaN")
                else:
                    self.validate_decimal_prompt.object = "<font color='red'>Invalid input. Please enter a valid decimal number.</font>"
        
        # Validate decimal input
        try:
            float(self.decimal.value)
            self.validate_decimal_prompt.object = "<font color='red'> </font>"
        except ValueError:
            self.validate_decimal_prompt.object = "<font color='red'>Invalid input. Please enter a valid decimal number.</font>"
        
            
    # check if input for exponent is valid
    # @param.depends('exponent.value', watch=True)
    def validate_exponent(self):
        # Check if decimal input is "NaN", allow empty exponent
        if self.decimal.value == "NaN" or self.decimal.value == "nan":
            self.validate_exponent_prompt.object = "<font color='red'> </font>"
            return
        
        # Check if value is empty or contains only whitespace
        if not self.exponent.value.strip():  
            self.validate_exponent_prompt.object = "<font color='red'>Field is empty. Please enter a whole exponent.</font>"
            return
        
        # Validate exponent input
        try:
            int(self.exponent.value)
            self.validate_exponent_prompt.object = "<font color='red'> </font>"
        except ValueError:
            self.validate_exponent_prompt.object = "<font color='red'>Invalid input. Please enter a valid whole exponent.</font>"

    # start computation
    def process_input(self, event=None):
        # update error prompts if not valid
        self.validate_decimal()
        self.validate_exponent()
        
        # handle special case: NaN
        if self.decimal.value == "NaN" or self.decimal.value == "nan":
            self.decimal_normalized = "NaN"
            self.case_decimal = "(NaN)"
            self.case_exponent = ""
            if self.exponent.value == "":
                self.exp = 0
            else:
                self.exp = self.exponent.value
            self.e_prime_dec = "NaN"
            self.e_prime_bits = "11111111"
            self.combo_bits = "11111"
            self.bcd_bits = "11111111111111111111"
            
            # get results
            self.bresult = str(self.sign) + str(self.combo_bits) + str(self.e_prime_bits)[2:] + str(self.bcd_bits)
            self.hresult = int(self.bresult, 2)
            self.hresult = hex(self.hresult)
            
            self.display_result()
            self.download_btn.disabled = False
            self.export_to_text_file(None)

        # do not proceed if at least one is empty or invalid
        elif self.decimal.value == "" or self.exponent.value == "" or self.validate_decimal_prompt.object != "<font color='red'> </font>" or self.validate_exponent_prompt.object != "<font color='red'> </font>":
            pass
        
        # proceed if all inputs are valid
        else:
            # normalize decimal
            self.normalize_decimal()
            # extract msd and update decimal
            if '-' in self.decimal_normalized:
                self.msd = self.decimal_normalized[1]
                self.decimal_last6 = self.decimal_normalized[2:]
            else:
                self.msd = self.decimal_normalized[0]
                self.decimal_last6 = self.decimal_normalized[1:]
            # handle case: zero
            if float(self.decimal.value) == 0:
                self.case_decimal = "(Zero)"
                self.case_exponent = ""
                self.exp = 0
            # handle special case: infinity
            if int(self.exp) > 90:
                self.case_decimal = ""
                self.case_exponent = "(Infinity)"
                self.e_prime_dec = "Infinity"
                self.e_prime_bits = "11111111"
                self.combo_bits = "11110"
                self.bcd_bits = "00000000000000000000"
            # handle case: denormalized
            elif int(self.exp) < -101:
                self.case_decimal = ""
                self.case_exponent = "(Denormalized)"
                self.e_prime_dec, self.e_prime_bits = compute_eprime(0) 
                self.combo_bits = compute_combination_bits(self.e_prime_bits, 0) 
                self.bcd_bits = "00000000000000000000"
            # handle case: zero and normal
            else:
                if int(self.exp) != 0:
                    self.case_decimal = ""
                    self.case_exponent = ""
                # get e-prime
                self.e_prime_dec, self.e_prime_bits = compute_eprime(self.exp) 
                # get combination bits
                self.combo_bits = compute_combination_bits(self.e_prime_bits, self.msd) 
                # convert to binary
                ms3b, ls3b = self.decimal_last6[:3], self.decimal_last6[3:] 
                # get bcd bits
                self.bcd_bits = bin_to_dpbcd(str_to_binary(ms3b)) + bin_to_dpbcd(str_to_binary(ls3b)) 

            # get results
            self.bresult = str(self.sign) + str(self.combo_bits) + str(self.e_prime_bits)[2:] + str(self.bcd_bits)
            self.hresult = int(self.bresult, 2)
            self.hresult = hex(self.hresult)
            
            self.display_result()
            self.download_btn.disabled = False
            self.export_to_text_file(None)
        
    # normalize decimal if needed
    @param.depends('rounding_method.value', watch=False)
    def normalize_decimal(self): 
        select = self.rounding_method.value
        self.decimal_normalized = str(self.decimal_unnormalized)
        self.exp = self.exponent.value
        
        # if decimal has decimal point, remove and recompute exponent
        if '.' in self.decimal_unnormalized:
            decimal_string = str(self.decimal_unnormalized) 
            integer_part, fractional_part = decimal_string.split('.')
            if len(integer_part) + len(fractional_part) < 7:
                base_10_exponent = len(integer_part) - (len(decimal_string)-1)
            else:
                base_10_exponent = len(integer_part) - 7
                
            integer_value = int(integer_part + fractional_part)
            self.decimal_normalized = str(integer_value) 
            self.exp = int(self.exponent.value) + base_10_exponent
        else:
            if len(self.decimal_unnormalized) < 7:
                base_10_exponent = 0
            else:
                base_10_exponent = len(self.decimal_unnormalized) - 7
                
            self.exp = int(self.exponent.value) + base_10_exponent
        
        # zero extend if decimal digits < 7
        if len(self.decimal_normalized) <= 7:
            zeros_needed = 7 - len(self.decimal_normalized)
            self.decimal_normalized = self.decimal_normalized.zfill(zeros_needed + len(self.decimal_normalized))
            if int(self.sign) == 1:
                self.decimal_normalized = "-" + self.decimal_normalized

        # choose rounding input if decimal digits > 7
        elif len(self.decimal_normalized) > 7:
            decimal_str = str(self.decimal_normalized) 
            if select == "Truncate":
                self.decimal_normalized = decimal_str[:7]
                if int(self.sign) == 1:
                    self.decimal_normalized = "-" + self.decimal_normalized
            elif select== "Round up": 
                if int(self.sign) == 0: # positive
                    self.decimal_normalized = decimal_str[:6] + str(int(decimal_str[6])+1)
                else: # negative
                    self.decimal_normalized = "-" + decimal_str[:7]
            elif select == "Round down":
                if int(self.sign) == 0: # positive
                    self.decimal_normalized = decimal_str[:7]
                else: # negative
                    self.decimal_normalized = "-" + decimal_str[:6] + str(int(decimal_str[6])+1)
            elif select == "Round to nearest ties to even":
                number_str, remaining = decimal_str[:6], decimal_str[6:]
                print(decimal_str[:6])
                print(decimal_str[6:])
                self.decimal_normalized = round_ties_to_even(number_str, remaining)
                if int(self.sign) == 1:
                    self.decimal_normalized = "-" + self.decimal_normalized

# Display blank results
    def display_blank_result(self):
        # Process
        self.normalized_decimal_text.object     = f"Normalized Decimal: <div style='{self.style_output1}'> &nbsp; </div>"
        self.exponent_text.object               = f"Final Exponent: <div style='{self.style_output1}'> &nbsp; </div>"
        self.e_prime_text.object                = f"E-Prime: <div style='{self.style_output1}'> &nbsp; </div>"
        self.sign_text.object                   = f"Sign Bit: <div style='{self.style_output8}'> &nbsp; </div>"
        self.combination_text.object            = f"Combination Bits: <div style='{self.style_output4}'> &nbsp; </div>"
        self.exponent_continuation_text.object  = f"Exponent Bits: <div style='{self.style_output5}'> &nbsp; </div>"
        self.bcd_bits_text.object               = f"Densely Packed BCD: <div style='{self.style_output6}'> &nbsp; </div>"
    
        # Output
        self.result_binary.object   = f"Final Answer (Binary): <div style='{self.style_output1}'> &nbsp; </div>"
        self.result_hex.object      = f"Final Answer (Hex): <div style='{self.style_output1}'> &nbsp; </div>"
    
# Display results
    def display_result(self):
        # Process
        self.normalized_decimal_text.object     = f"Normalized Decimal: <div style='{self.style_output1}'>{self.decimal_normalized} {self.case_decimal}</div>"
        self.exponent_text.object               = f"Final Exponent: <div style='{self.style_output1}'>{self.exp} {self.case_exponent}</div>"
        self.e_prime_text.object                = f"E-Prime: <div style='{self.style_output1}'>{self.e_prime_dec} → {self.e_prime_bits}</div>"
        self.sign_text.object                   = f"Sign Bit: <div style='{self.style_output8}'>{self.sign}</div>"
        self.combination_text.object            = f"Combination Bits: <div style='{self.style_output4}'>{self.combo_bits}</div>"
        self.exponent_continuation_text.object  = f"Exponent Bits: <div style='{self.style_output5}'>{self.e_prime_bits[2:]}</div>"
        self.bcd_bits_text.object               = f"Densely Packed BCD: <div style='{self.style_output6}'>{self.bcd_bits}</div>"
    
        # Output
        self.result_binary.object = f"Final Answer (Binary): <div style='{self.style_output1}'>" \
                                    f"<span style='background-color: #F0D1D4; display: inline-block;'> {self.sign} </span> &nbsp;" \
                                    f"<span style='background-color: #C1DBDA; display: inline-block;'> {self.combo_bits} </span> &nbsp;" \
                                    f"<span style='background-color: #D1C2D9; display: inline-block;'> {str(self.e_prime_bits)[2:]} </span> &nbsp;" \
                                    f"<span style='background-color: #E2BFB3; display: inline-block;'> {' '.join([self.bcd_bits[i:i+4] for i in range(0, len(self.bcd_bits), 4)])} </span>" \
                                    "</div>"
    
        self.result_hex.object = f"Final Answer (Hex): <div style='{self.style_output7}'>{str(self.hresult).upper()}</div>" 

# Functionality to export the results in a text file
    def export_to_text_file(self, event):
        try:
            contents = [
                f"IEEE-754 Decimal-32 Floating-Point Converter",
                f"Inputs",
                f"Decimal               : {self.decimal_normalized}",
                f"Exponent (Base-10)    : {self.exp}",
                f"Rounding Method       : {self.rounding_method.value}",
                f"",
                f"Process",
                f"Normalized Decimal    : {self.decimal_normalized} {self.case_decimal}",
                f"Final Exponent        : {self.exp} {self.case_exponent}",
                f"E-Prime               : {self.e_prime_dec} -> {self.e_prime_bits}",
                f"",
                f"Output",
                f"Sign Bit              : {self.sign}",
                f"Combination Bits      : {self.combo_bits}",
                f"Exponent Bits         : {self.e_prime_bits[2:]}",
                f"Densely Packed BCD    : {self.bcd_bits}",
                f"",
                f"Final Answer (Binary) : {self.sign}  {self.combo_bits}  {str(self.e_prime_bits)[2:]}  {self.bcd_bits}",
                f"Final Answer (Hex)    : {str(self.hresult).upper()}",
                f""
            ]

            # Path to downloads folder
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write('\n'.join(contents))
                temp_file.flush() # Ensure all data is written to the file
                temp_file_path = temp_file.name

            # Rename the temporary file to the desired name
            desired_file_path = os.path.join(os.path.dirname(temp_file_path), "exported_content.txt")
            
            # Check if the destination file already exists and remove it if it does
            if os.path.exists(desired_file_path):
                os.remove(desired_file_path)
            
            os.rename(temp_file_path, desired_file_path)
    
            # pn.state.notifications.success('Export successful! Check your temporary files.', duration=5000)
    
            # Update the downloadable file with the generated file
            self.download_btn.filename = "exported_content.txt"
            self.download_btn.file = desired_file_path
    
        except Exception as e:
            print(e)
            pn.state.notifications.error('An error occurred while creating the temporary file.', duration=5000)
            self.normalized_decimal_text.object = f"{str(e)}"

    @param.depends('download_btn._clicks', watch=True)
    def export_notification(event):
        pn.state.notifications.success('Export successful! Check your downloads folder.', duration=5000)

# In[16]:


converter = Converter()
converter.compute_btn.on_click(converter.process_input)
converter.export_to_text_file(None)
converter_container = pn.Column(
    pn.Row(
        pn.Column(
            "## Input",
            converter.decimal,
            converter.validate_decimal_prompt,
            converter.exponent,
            converter.validate_exponent_prompt,
            converter.rounding_method,
            pn.layout.Spacer(height=30),
            converter.compute_btn,
            pn.layout.Spacer(height=15),
            converter.download_btn,
            min_width=145
        ),
        pn.Column(
            "## Process",
            converter.normalized_decimal_text,
            converter.exponent_text,
            converter.e_prime_text,
            min_width=145,
            max_width=200
        ),
        pn.Column(
            "## Output",
            converter.sign_text,
            converter.combination_text,
            converter.exponent_continuation_text,
            converter.bcd_bits_text,
            converter.result_binary,
            converter.result_hex,
            pn.layout.Spacer(height=15),
            min_width=145
        ),
    ),
)

# Define default template parameters
ACCENT_COLOR = "#AAC8A7"
DEFAULT_PARAMS = {
    "site": "CSARCH2 Simulation",
    "accent_base_color": ACCENT_COLOR,
    "header_background": ACCENT_COLOR,
}

# Create a main Column for the current page
main = pn.Column(converter_container)
converter.display_blank_result()

# Create the FastListTemplate with documentation in the sidebar
template = pn.template.FastListTemplate(
    title="IEEE-754 Decimal-32 Floating-Point Converter",
    sidebar=[
        pn.pane.Markdown("## Reports"),
        pn.pane.Markdown("### Developed by:"),
        pn.pane.Markdown("CSARCH2 S12 Group 2"),
        pn.pane.Markdown("Amelia Abenoja, Zhoe Aeris Gon Gon, Harold Mojica, Anne Gabrielle Sulit, Ysobella Torio"),
   ],
    main=[main],
    **DEFAULT_PARAMS,
)#.servable(title="IEEE-754 Decimal-32 Floating-Point Converter")

# Serve the app
pn.serve(template, port=5006)


# IEEE-754 Decimal-32 floating-point converter (including all special cases)
# 
# Input: Decimal and base-10 (i.e., 127.0x105) – should be able to handle more than 7
# digits properly (provide an option for the user to choose rounding method). Also, should
# support special cases (i.e., NaN).
# 
# Output: (1) binary output with space between sections (2) its hexadecimal equivalent (3)
# with the option to output in the text file.
