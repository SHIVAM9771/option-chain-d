import json
from BSM import BSM
from time_cal import get_time_diff_in_days


def reversal_calculator(option_chain, exp):
    try:
        # Extract data from option_chain
        data = option_chain["data"]["oc"]
        sltp = option_chain["data"]["sltp"]

        # Convert strikes to float and calculate time in days
        strikes = [float(strike) for strike in data.keys()]
        T = get_time_diff_in_days(int(exp))

        # Initialize lists for CE and PE values
        ce_iv, ce_ltp, ce_delta = [], [], []
        pe_iv, pe_ltp, pe_delta = [], [], []

        # Extract CE and PE data
        for values in data.values():
            ce_data = values.get("ce", {})
            pe_data = values.get("pe", {})

            # Append values with fallback to 0 if key doesn't exist
            ce_iv.append(float(ce_data.get("iv", 0)))
            ce_ltp.append(float(ce_data.get("ltp", 0)))
            ce_delta.append(float(ce_data.get("optgeeks", {}).get("delta", 0)))

            pe_iv.append(float(pe_data.get("iv", 0)))
            pe_ltp.append(float(pe_data.get("ltp", 0)))
            pe_delta.append(float(pe_data.get("optgeeks", {}).get("delta", 0)))

        # Calculate reversals for each strike and store results in option_chain
        for i, strike in enumerate(strikes):
            strike_key = int(strike)  # Convert strike back to string to match data keys
            if str(strike_key) not in data.keys():
                print(f"Strike {strike_key} not found in data.")
                continue  # Skip this strike if key is not found

            try:
                # Call the BSM get_reversal function
                reversal_data = BSM.get_reversal(
                    sltp,
                    strike_key,
                    T,
                    ce_iv[i],
                    pe_iv[i],
                    ce_ltp[i],
                    pe_ltp[i],
                    ce_delta[i],
                    pe_delta[i],
                )

                # Add the reversal data to option_chain
                data[str(strike_key)]["reversal"] = reversal_data

            except Exception as e:
                print(f"Error calculating reversal for strike {strike}: {e}")
                continue  # Continue with the next strike in case of error

        return option_chain  # Return the modified option_chain with reversal data

    except json.JSONDecodeError as e:
        print("Error reading JSON data:", e)
        return option_chain
    except FileNotFoundError as e:
        print("Error: JSON file not found:", e)
        return option_chain
    except Exception as e:
        print("An unexpected error occurred:", e)
        return option_chain


# Example usage:
# Assume option_chain is a dictionary loaded with JSON data
# exp = some integer timestamp or value for expiration
# modified_option_chain = reversal_calculator(option_chain, exp)
# print(json.dumps(modified_option_chain, indent=2))
