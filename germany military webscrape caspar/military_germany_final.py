# Version change: unique matching only with 100% matches and human_check column, if previous commitment is retrospectively increased we also adjust the Newly committed column for consistency
# TODO 
import time
import re
import requests # requires pip install
from bs4 import BeautifulSoup # requires pip install
import pandas as pd # requires pip install
from fuzzywuzzy import fuzz # requires pip install fuzzywuzzy[speedup]
# also need pip install openpyxl (to write to excel)

df_committed = pd.DataFrame()
df_delivered = pd.DataFrame()

all_website_dates = []  # list for all dates
date_index = 0 # counter to correctly label the headers of the df with the appropriate
timeout = 0 # counter to see how many iterations we already did -> one iteration = 1 day
total_weapons_delivered = [] # collects all unique entries of weapon deliveries
total_weapons_committed = [] # collects all unique entries of weapon committments
# list to keep track of the indices we already matched against to make sure they don't get used more than once
matched_indices_change_delivered = [] # needed to avoid matching the same entry twice
matched_indices_newly_committed = []
matched_indices_newly_delivered = []

european_countries = [ # used for cleaning of entries later on
    "Albania", "Albanian",
    "Andorra", "Andorran",
    "Austria", "Austrian",
    "Belarus", "Belarusian",
    "Belgium", "Belgian",
    "Bosnia and Herzegovina", "Bosnian",
    "Bulgaria", "Bulgarian",
    "Croatia", "Croatian",
    "Cyprus", "Cypriot",
    "Czech Republic", "Czech",
    "Denmark", "Danish",
    "Estonia", "Estonian",
    "Finland", "Finnish",
    "France", "French",
    "Germany", "German",
    "Greece", "Greek",
    "Hungary", "Hungarian",
    "Iceland", "Icelander",
    "Ireland", "Irish",
    "Italy", "Italian",
    "Kosovo", "Kosovar",
    "Latvia", "Latvian",
    "Liechtenstein", "Liechtensteiner",
    "Lithuania", "Lithuanian",
    "Luxembourg", "Luxembourger",
    "Malta", "Maltese",
    "Moldova", "Moldovan",
    "Monaco", "Monegasque",
    "Montenegro", "Montenegrin",
    "Netherlands", "Dutch",
    "North Macedonia", "Macedonian",
    "Norway", "Norwegian",
    "Poland", "Polish",
    "Portugal", "Portuguese",
    "Romania", "Romanian",
    "Serbia", "Serbian",
    "Slovakia", "Slovak",
    "Slovenia", "Slovene",
    "Spain", "Spanish",
    "Sweden", "Swedish",
    "Switzerland", "Swiss",
    "Turkey", "Turkish",
    "Ukraine", "Ukrainian",
    "United Kingdom", "British"
]

def main():
    global df_delivered
    global df_committed
    global date_index
    max_day = 31
    max_month = 1200
    variable_urlpart = 20220623 # first snapshot it at 20220623 
    while variable_urlpart < 20240226: # put the TIMEFRAME your interested here 
        if variable_urlpart % 100 < max_day: # day counter
            variable_urlpart += 1 # adds one day
            try:
                website_date, uniquedate_url = scrapedate(str(variable_urlpart)) # returns website date and the url of that date
            except TypeError: # filter out redirects from Wayback (some urls are redirects to other urls)
                pass
            else:
                if website_date: # include if statement to ensure that it only appends to the list if it finds something ( a date that includes a "tuesday" eg to ensure it writes only then to the list)
                    if website_date not in all_website_dates:
                        all_website_dates.append(website_date) # add date to list for referencing and creating unique headers
                        if 20221201 <= variable_urlpart <= 20221214: # checks the 2 entries with changes in format (no unformated list here, just bpa-richtext here) -> this is still "hardcoded" to check for these 2 ENTRIES ONLY
                            amount_committed, weapon_committed, amount_delivered, weapon_delivered = scrape_list_bpa(uniquedate_url)
                        else: # standard scraping technique for all other entries
                            amount_committed, weapon_committed, amount_delivered, weapon_delivered = scrape_list(uniquedate_url)
                        # add up values of double entries for better consistency (yes sometimes there are double entries)
                        add_doubles(amount_committed, weapon_committed)
                        add_doubles(amount_delivered, weapon_delivered)
                        # get dimensions and column names of the current entries -> needed to have the committed and delivered df equal in length in the end
                        max_length_local_c = set_dimensions(amount_committed, weapon_committed, df_committed)
                        max_length_local_d = set_dimensions(amount_delivered, weapon_delivered, df_delivered)
                        max_length_global = max(max_length_local_c, max_length_local_d) # maximum length of all all entries in any df at that time
                        # update the dataframe with the new data, ensuring equal length of both dfs
                        write_to_df_delivered(amount_delivered, weapon_delivered, max_length_global)
                        write_to_df_committed(amount_committed, weapon_committed, max_length_global)
                        # clean excess entries
                        df_committed.apply(cleanup_committed, axis=1, df_comm = df_committed)
                        df_delivered.apply(cleanup_delivered, axis=1, df_deli =df_delivered)
                        date_index += 1

        elif variable_urlpart % 10000 < max_month: # month counter
            variable_urlpart += 70 # adds one month (100) and substracts 30 days
            try:
                website_date, uniquedate_url = scrapedate(str(variable_urlpart))
            except TypeError:
                pass
            else:
                if website_date:
                    if (website_date) not in all_website_dates:
                        all_website_dates.append(website_date)
                        if 20221201 <= variable_urlpart <= 20221214:
                            amount_committed, weapon_committed, amount_delivered, weapon_delivered = scrape_list_bpa(uniquedate_url)
                        else:
                            amount_committed, weapon_committed, amount_delivered, weapon_delivered = scrape_list(uniquedate_url)
                        add_doubles(amount_committed, weapon_committed)
                        add_doubles(amount_delivered, weapon_delivered)
                        max_length_local_c = set_dimensions(amount_committed, weapon_committed, df_committed)
                        max_length_local_d = set_dimensions(amount_delivered, weapon_delivered, df_delivered)
                        max_length_global = max(max_length_local_c, max_length_local_d)
                        write_to_df_delivered(amount_delivered, weapon_delivered, max_length_global)
                        write_to_df_committed(amount_committed, weapon_committed, max_length_global)
                        df_committed.apply(cleanup_committed, axis=1, df_comm = df_committed)
                        df_delivered.apply(cleanup_delivered, axis=1, df_deli =df_delivered)
                        date_index += 1

        else:
            variable_urlpart += 8870 # year counter, adds one year (10000) and substracts 11 months (1100) and 30 days to get back to the 01.01.YYYY
            try:
                website_date, uniquedate_url = scrapedate(str(variable_urlpart))
            except TypeError:
                pass
            else:
                if website_date:
                    if (website_date) not in all_website_dates:
                        all_website_dates.append(website_date) 
                        if 20221201 <= variable_urlpart <= 20221214:
                            amount_committed, weapon_committed, amount_delivered, weapon_delivered = scrape_list_bpa(uniquedate_url)
                        else:
                            amount_committed, weapon_committed, amount_delivered, weapon_delivered = scrape_list(uniquedate_url)
                        add_doubles(amount_committed, weapon_committed)
                        add_doubles(amount_delivered, weapon_delivered)
                        max_length_local_c = set_dimensions(amount_committed, weapon_committed, df_committed)
                        max_length_local_d = set_dimensions(amount_delivered, weapon_delivered, df_delivered)
                        max_length_global = max(max_length_local_c, max_length_local_d)
                        write_to_df_delivered(amount_delivered, weapon_delivered, max_length_global)
                        write_to_df_committed(amount_committed, weapon_committed, max_length_global)
                        df_committed.apply(cleanup_committed, axis=1, df_comm = df_committed)
                        df_delivered.apply(cleanup_delivered, axis=1, df_deli =df_delivered)
                        date_index += 1

    # converts all integers that are currently still saved as strings to int
    df_committed = df_committed.map(try_convert_to_int)
    df_delivered = df_delivered.map(try_convert_to_int)
    # write to one excel file
    with pd.ExcelWriter("military_output.xlsx") as writer:
        df_committed.to_excel(writer, sheet_name="committed", index=False, freeze_panes=(1,0))
        df_delivered.to_excel(writer, sheet_name="delivered", index=False, freeze_panes=(1,0))

def strip_dataframes(df):
    global date_index
    # preprocesses the dataframe for increased matching precision
    df_stripped = df.copy()
    df_stripped[f"{all_website_dates[date_index]} Description"] = df_stripped[f"{all_website_dates[date_index]} Description"].str.replace(r" including.*$", "", regex=True).str.replace(r" with.*$", "", regex = True).str.replace(r" \(including.*$", "", regex=True).str.replace(" (from Bundeswehr and industry stocks)", "")
    df_stripped[f"{all_website_dates[date_index - 1]} Description"] = df_stripped[f"{all_website_dates[date_index - 1]} Description"].str.replace(r" including.*$", "", regex=True).str.replace(r" with.*$", "", regex = True).str.replace(r" \(including.*$", "", regex=True).str.replace(" (from Bundeswehr and industry stocks)", "")

    pattern = r"\b(" + "|".join(european_countries) + r")\b" 
    for i, line in df_stripped.iterrows():
        df_stripped.loc[i, f"{all_website_dates[date_index]} Description"] = re.sub(r"\([^)]*" + pattern + r"[^)]*\)", "", line[f"{all_website_dates[date_index]} Description"]).strip()
        df_stripped.loc[i, f"{all_website_dates[date_index - 1]} Description"] = re.sub(r"\([^)]*" + pattern + r"[^)]*\)", "", line[f"{all_website_dates[date_index - 1]} Description"]).strip()
    
    return df_stripped

def strip_target_weapon(t_weapon):
    # preprocesses the newly added weapon we are trying to match against the old entries
    pattern = r"\b(" + "|".join(european_countries) + r")\b" 
    stripped_tw = t_weapon.replace(" (from Bundeswehr and industry stocks)", "")
    stripped_tw = re.sub(r" including.*$", "", stripped_tw)
    stripped_tw = re.sub(r" with.*$", "", stripped_tw)
    stripped_tw = re.sub(r" \(including.*$", "", stripped_tw)
    stripped_tw = re.sub(r"\([^)]*" + pattern + r"[^)]*\)", "",stripped_tw)

    return stripped_tw

def calculate_change_delivered(row, df_deli): # for more detailed examples look at seperate function with tutorial
    global date_index # date_index is new date, date_index -1 is baseline
    best_match_score = -1  # start best match score (fuzzy.ratio ranges from [0-100] so -1 ensures that score/index will always be updated (bit arbitrary could also be set to 0))
    best_match_index = -1  # start index of best match 

    target_weapon = row[f"{all_website_dates[date_index]} Description"] # define target key that will be used to match entries
    stripped_target_weapon = strip_target_weapon(target_weapon)
    stripped_df = strip_dataframes(df_deli)
    
    new_delivered_value = row[f"{all_website_dates[date_index]} Amount"]

    for index, baseline_weapon in enumerate(stripped_df[f"{all_website_dates[date_index - 1]} Description"]): # iterate through all baseline_weapons and match to new_weapon
        if index not in matched_indices_change_delivered:
            similarity_score = fuzz.token_sort_ratio(baseline_weapon.lower(), stripped_target_weapon.lower()) # create similarity score based on baseline/new weapon irrespectively of word order (Levenshtein distance)
            if similarity_score > best_match_score:
                best_match_score = similarity_score
                best_match_index = index

    if best_match_score > 80:  # if the current target_value is matched with a baseline entry with >75%, we retrieve the baseline_amount of that weapon 
        if best_match_score == 100: # only "take away" the matches that are 100% exact, not for fuzzy matching
            matched_indices_change_delivered.append(best_match_index)  # add the matched index to the list
        baseline_value = df_deli.at[best_match_index, f"{all_website_dates[date_index - 1]} Amount"]
        try:
            change = int(new_delivered_value) - int(baseline_value) # then calculate the difference btw new and baseline amount 
            if change == 0:
                change = "no change" # for clarity, could also leave as 0
        except ValueError:
            try: # if one amount goes from undisclosed to int, we capture the now disclosed amount
                change = int(new_delivered_value)        
            except ValueError: # in case of two undisclosed amounts
                if new_delivered_value != "":
                    change = "no change"
                else: # not necessary, leave in for good measure, cleanup could take care of it
                    change = ""
        if new_delivered_value != "": # not necessary, leave in for good measure, cleanup could take care of it
            df_deli.at[row.name, f"{all_website_dates[date_index]} New Item [Dummy]"] = "No"
        
    else: # if match threshold is not reached, differentiate between new entries and empty cells
        if target_weapon != "":
            df_deli.at[row.name, f"{all_website_dates[date_index]} New Item [Dummy]"] = "Yes"
            change = new_delivered_value # if we have a new entry, mark change as total of what is NEW
        elif target_weapon == "":
            change = "" # if the new_weapon entry is empty, just append an empty string

    # update the new_change column directly in the function
    df_deli.at[row.name, f"{all_website_dates[date_index]} Change"] = change

    # Add human check column for person checking entries (marks all New Items, non perfect matches and strange values for change as "CHECK")
    try:
        change = int(change)
    except ValueError:
        if best_match_score != 100:
            df_deli.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "CHECK"
        else:
            df_deli.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "No"
    else:
        if best_match_score != 100 or change > 1000 or change < 0:
            df_deli.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "CHECK"
        else:
            df_deli.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "No"   

def calculate_change_committed(row, df_comm):
    global date_index # date_index is new date, date_index -1 is baseline
    
    # create copies of the delivered and committed df to manipulate entries for better matching precision (only used for matching, not for writing)
    df_committed_clean = strip_dataframes(df_comm)
    df_delivered_clean = strip_dataframes(df_delivered)
    
    def newly_committed(): # gives Newly Committed Column
        # define target key that will be used to match entries
        target_weapon = row[f"{all_website_dates[date_index]} Description"] 
        stripped_target_weapon = strip_target_weapon(target_weapon)

        new_committed_value = row[f"{all_website_dates[date_index]} Amount"]
        best_match_score = -1  # start best match score (fuzzy.ratio ranges from [0-100] so -1 ensures that score/index will always be updated
        best_match_index = -1  # start index of best match
        
        for index, baseline_weapon in enumerate(df_committed_clean[f"{all_website_dates[date_index - 1]} Description"]): # iterate through all baseline_weapons and match to new_weapon
            if index not in matched_indices_newly_committed: # ensure non_double matching of entries
                similarity_score = fuzz.token_sort_ratio(baseline_weapon.lower(), stripped_target_weapon.lower()) # create similarity score based on baseline/new weapon irrespectively of word order (Levenshtein distance)
                if similarity_score > best_match_score:
                    best_match_score = similarity_score
                    best_match_index = index
### Calculate change (Newly Committed Value)    
        if best_match_score > 75:  # if the current target_value is matched with a baseline entry with >75%, we retrieve the baseline_amount of that weapon 
            if best_match_score == 100:
                matched_indices_newly_committed.append(best_match_index)
            baseline_value = df_committed_clean.at[best_match_index, f"{all_website_dates[date_index - 1]} Amount"]
            try:
                change = int(new_committed_value) - int(baseline_value) # then calculate the difference btw new and baseline amount 
                if change == 0:
                    change = "no change" # for clarity, could also leave as 0
            except ValueError:
                try: # if one amount goes from undisclosed to int, we capture the now disclosed amount
                    change = int(new_committed_value)        
                except ValueError: # in case of two undisclosed amounts
                    if new_committed_value != "":
                        change = "no change"
                    else:
                        change = ""
            if new_committed_value != "": # avoid writing to empty entries, set dummy to "No" as we're comparing to an old entry
                df_comm.at[row.name, f"{all_website_dates[date_index]} New Item [Dummy]"] = "No"
        
        else:
            if target_weapon != "":
                df_comm.at[row.name, f"{all_website_dates[date_index]} New Item [Dummy]"] = "Yes"
                change = new_committed_value # if we have a new entry, change is set to the amount of that new value
            else:
                change = "" # if the new_weapon entry is empty, just write an empty string
### Changes committed calculated done
### update the new_change column directly in the function
        newly_delivered_value = row[f"{all_website_dates[date_index]} Newly Delivered"]
        if isinstance(change, int):
            try:
                newly_delivered_value = int(newly_delivered_value)
            except ValueError:
                df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Committed"] = change  # If newly delivered is not an int just take change in committed_new - committed_old
            else:
                total_change = change + newly_delivered_value # change including changes in delivery (Total change = committed_new - committed_old + delivered_new)
                if total_change == 0:
                    df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Committed"] = "no change" # for clarity could also leave as 0
                else:
                    df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Committed"] = total_change

        elif isinstance(newly_delivered_value, int):# if we only have an entry for a newly delivered Item, but committed_new - committed_old = "no change" 
            if df_comm.at[row.name, f"{all_website_dates[date_index]} Amount"] != "undisclosed":
                df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Committed"] = newly_delivered_value #update newly committed to the delivered value
            else:
                df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Committed"] = df_comm.at[row.name, f"{all_website_dates[date_index]} Amount"]
        
        else: # if newly_delivered is not an integer, eg "no change", we just take change = committed_new - committed_old, this also copies "no change" if change = "no change"
            df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Committed"] = change
        
### changes have been updated
### Now update the previous amount if Newly_delivered > committed_old assuming that everything needs to be committed before it can be delivered     
### First fully deplete the stock of committed and then treat everything on top as extra if Newly_d > Old_c
            
        # find weapon of the newly delivered amount and the corresponding index in the description of the previous entry to correcly index old_committed_int
        wp = df_comm.at[best_match_index, f"{all_website_dates[date_index]} Description"]
        # find closest match using fuzz.sort_token_ratio to ensure fuzzy matching
        matches = df_comm[f"{all_website_dates[date_index - 1]} Description"].apply(lambda x: fuzz.token_sort_ratio(x, wp)) # matches is a Series object containing the similarity scores for each description in the column (x is previous Description, wp current)
        closest_match_index = matches.idxmax() # get index of highest similarity score in the matches series (index for the "Previous Entry Description")
        
        # prematurely write all Previous Commitment increased Dummies to "No" to then only change the instances where we did change the previous commitment
        df_comm.at[row.name, f"{all_website_dates[date_index]} Previous Commitment increased [Dummy]"] = "No" 
        
        if matches[closest_match_index] >= 75: # use same threshold as before for consistency
            row_wp_increased = closest_match_index
            try:
                newly_delivered_int = int(df_comm.at[best_match_index, f"{all_website_dates[date_index]} Newly Delivered"])
                old_committed_int = int(df_comm.at[row_wp_increased, f"{all_website_dates[date_index - 1]} Amount"])
                old_newly_committed_int = int(df_comm.at[row_wp_increased, f"{all_website_dates[date_index - 1]} Newly Committed"])
            except ValueError:
                pass
            else:
                if newly_delivered_int > old_committed_int:
                    increment = newly_delivered_int - old_committed_int
                    df_comm.at[row_wp_increased, f"{all_website_dates[date_index - 1]} Amount"] = old_committed_int + increment
                    new_old_committed_int = int(df_comm.at[row_wp_increased, f"{all_website_dates[date_index - 1]} Amount"])
                    df_comm.at[best_match_index, f"{all_website_dates[date_index]} Previous Commitment increased [Dummy]"] = "Yes"
                    df_comm.at[best_match_index, f"{all_website_dates[date_index]} Newly Committed"] = df_comm.at[best_match_index, f"{all_website_dates[date_index]} Amount"]
                    # correct old Newly committed entry
                    df_comm.at[row_wp_increased, f"{all_website_dates[date_index - 1]} Newly Committed"] = new_old_committed_int - old_committed_int + old_newly_committed_int

        # populate human check column (mark outliers)
        human_check(row, best_match_score)

    def newly_delivered():
        # match each entry in the delivered sheet under Change and find the corresponding entry in the committed sheet under the current description, then write it to Newly Delivered
        target_weapon = row[f"{all_website_dates[date_index]} Description"] # define target key that will be used to match entries (the committed description)
        stripped_target_weapon = strip_target_weapon(target_weapon)
        # update the Newly Delivered Column in the committed sheet (need fuzzy matching again)
        best_corresponding_row_index = -1
        best_corresponding_score = -1

        for index, baseline_weapon in enumerate(df_delivered_clean[f"{all_website_dates[date_index]} Description"]):
            if index not in matched_indices_newly_delivered:
                similarity_score = fuzz.token_sort_ratio(baseline_weapon.lower(), stripped_target_weapon.lower())
                if similarity_score > best_corresponding_score:
                    best_corresponding_score = similarity_score
                    best_corresponding_row_index = index

        # update "Newly Delivered" column in the commmitted df with change value from df_delivered
        if best_corresponding_row_index != -1 and best_corresponding_score >= 75: # if the matching precision is larger/equal to 75 (Levenshtein-Distance), write the change from the delivered sheet
            if best_corresponding_score == 100: # only take away perfect matches from matching more than once
                matched_indices_newly_delivered.append(best_corresponding_row_index)
            change_delivered = df_delivered.at[best_corresponding_row_index, f"{all_website_dates[date_index]} Change"]
            df_committed.at[row.name, f"{all_website_dates[date_index]} Newly Delivered"] = change_delivered 
        else: # meaning no match -> cannot be a delivery so mark as "no change" for consistency
            df_committed.at[row.name, f"{all_website_dates[date_index]} Newly Delivered"] = "no change"

    def new_entry():
        # New Item: Delivery w/o Commitment
        if df_delivered.at[row.name, f"{all_website_dates[date_index]} New Item [Dummy]"] == "Yes":
            # the first two if statements check if there's a new delivery that is not yet under the new committed entry
            new_item = df_delivered.at[row.name, f"{all_website_dates[date_index]} Description"]
            new_entries_committed = df_comm[f"{all_website_dates[date_index]} Description"].tolist()
            if new_item not in new_entries_committed:
                # write the delivery w/o commitment to committed new for data consistency
                # function checks which values of the delivered df are not in the committed df at the desired key, writes them to a list 
                values_to_fill = df_delivered.loc[~(df_delivered[f"{all_website_dates[date_index]} Description"].isin(new_entries_committed)) & (df_delivered[f"{all_website_dates[date_index]} New Item [Dummy]"] == "Yes"), f"{all_website_dates[date_index]} Description"].tolist()
                
                # get indices of blank entries in the committed df
                blank_indices = df_comm.index[df_comm[f"{all_website_dates[date_index]} Description"] == ""].tolist()
                # fill each blank entry in the committed df with corresponding value from the delivered df
                for index, value in zip(blank_indices, values_to_fill):
                    df_comm.at[index, f"{all_website_dates[date_index]} Description"] = value
                    amount_of_value = df_delivered.loc[df_delivered[f"{all_website_dates[date_index]} Description"] == value, f"{all_website_dates[date_index]} Amount"].iloc[0] # get corresponding amount of value
                    df_comm.at[index, f"{all_website_dates[date_index]} Amount"] = amount_of_value
                    df_comm.at[index, f"{all_website_dates[date_index]} New Item [Dummy]"] = "Yes"
                    df_comm.at[index, f"{all_website_dates[date_index]} Newly Delivered"] = df_comm.at[index, f"{all_website_dates[date_index]} Amount"]
                    df_comm.at[index, f"{all_website_dates[date_index]} Newly Committed"] = df_comm.at[index, f"{all_website_dates[date_index]} Amount"]
                    df_comm.at[index, f"{all_website_dates[date_index]} Previous Commitment increased [Dummy]"] = "No"

    def last_occurrence(df): # uses fuzzy matching, still needs to use stripped values
        # use stripped df to ensure higher matching precision
        stripped_df = strip_dataframes(df)

        df.at[row.name, f"{all_website_dates[date_index - 1]} Last Occurrence [Dummy]"] = "Yes"
        for _, rw in df[df[f"{all_website_dates[date_index]} New Item [Dummy]"] == "No"].iterrows(): # go through all unstripped entries in the df and get the description where New Item == "No"
            desc = rw[f"{all_website_dates[date_index]} Description"]  # get the description
            stripped_desc = strip_target_weapon(desc) # also here for higher precision
            # perform fuzzy matching
            match_index = -1
            max_similarity = -1
            for idx, description in stripped_df[f"{all_website_dates[date_index - 1]} Description"].items():
                similarity = fuzz.token_sort_ratio(stripped_desc, description)
                if similarity >= 75 and similarity > max_similarity:
                    max_similarity = similarity
                    match_index = idx

            # check if there's a match (avoiding potential IndexError)
            if match_index != -1:
                # update the corresponding "Last Occurrence" with the matched description
                df.at[match_index, f"{all_website_dates[date_index - 1]} Last Occurrence [Dummy]"] = "No"

    newly_delivered() # fills newly delivered column
    newly_committed() # fills newly committed column
    last_occurrence(df_delivered) # fills last occurrence column
    last_occurrence(df_comm)
    new_entry() # updates df if we have a new delivery w/o commitment (writes delivered to committed df)

def human_check(row, best_match_score):
    global date_index
    try: # use 2 try statements to allow for better precision
        newly_committed_int = int(df_committed.at[row.name, f"{all_website_dates[date_index]} Newly Committed"])  
    except ValueError:
        try:
            newly_delivered_int = int(df_committed.at[row.name, f"{all_website_dates[date_index]} Newly Delivered"])
        except ValueError:        
            if best_match_score != 100:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "CHECK"
            else:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "No"
        else:
            if best_match_score != 100 or newly_delivered_int > 1000 or newly_delivered_int < 0:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "CHECK"
            else:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "No"
    else:
        try:
            newly_delivered_int = int(df_committed.at[row.name, f"{all_website_dates[date_index]} Newly Delivered"])
        except ValueError:
            if best_match_score != 100 or newly_committed_int > 1000 or newly_committed_int < 0:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "CHECK"
            else:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "No"
        else:    
            if best_match_score != 100 or newly_committed_int > 1000 or newly_committed_int < 0 or newly_delivered_int > 1000 or newly_delivered_int < 0:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "CHECK"
            else:
                df_committed.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = "No"

def cleanup_committed(row, df_comm): # little clean-up
    global date_index
    if df_comm.at[row.name, f"{all_website_dates[date_index]} Description"] == "":
        df_comm.at[row.name, f"{all_website_dates[date_index]} Previous Commitment increased [Dummy]"] = ""
        df_comm.at[row.name, f"{all_website_dates[date_index]} Newly Delivered"] = ""
        df_comm.at[row.name, f"{all_website_dates[date_index]} Last Occurrence [Dummy]"] = ""
        df_comm.at[row.name, f"{all_website_dates[date_index]}"] = ""
        df_comm.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = ""
    try:
        if df_comm.at[row.name, f"{all_website_dates[date_index - 1]} Description"] == "":
            df_comm.at[row.name, f"{all_website_dates[date_index - 1]} Last Occurrence [Dummy]"] = ""
            df_comm.at[row.name, f"{all_website_dates[date_index - 1]}"] = ""
    except IndexError:
        pass
    try:
        if df_comm.at[row.name, f"{all_website_dates[date_index - 2]} Description"] == "":
            df_comm.at[row.name, f"{all_website_dates[date_index - 2]} Last Occurrence [Dummy]"] = ""
            df_comm.at[row.name, f"{all_website_dates[date_index - 2]}"] = ""
    except IndexError:
        pass

def cleanup_delivered(row, df_deli):
    global date_index
    if df_deli.at[row.name, f"{all_website_dates[date_index]} Description"] == "":
        df_deli.at[row.name, f"{all_website_dates[date_index]} Last Occurrence [Dummy]"] = ""
        df_deli.at[row.name, f"{all_website_dates[date_index]}"] = ""
        df_deli.at[row.name, f"{all_website_dates[date_index]} HUMAN CHECK"] = ""
    
    try:
        if df_deli.at[row.name, f"{all_website_dates[date_index - 1]} Description"] == "":
            df_deli.at[row.name, f"{all_website_dates[date_index - 1]} Last Occurrence [Dummy]"] = ""
            df_deli.at[row.name, f"{all_website_dates[date_index - 1]}"] = ""
    except IndexError:
        pass
    try:
        if df_deli.at[row.name, f"{all_website_dates[date_index - 2]} Description"] == "":
            df_deli.at[row.name, f"{all_website_dates[date_index - 2]} Last Occurrence [Dummy]"] = ""
            df_deli.at[row.name, f"{all_website_dates[date_index - 2]}"] = ""
    except IndexError:
        pass

def add_doubles(amount, weapon):
    # create temporary dictionary to store the two lists
    data_dict = {}
    data_dict["amount"] = amount
    data_dict["weapon"] = weapon
    # create temporary dictionary to store summed amounts for each weapon
    weapon_amounts = {}

    # iterate over two lists (amount/weapon) via zip()
    for a, w in zip(data_dict["amount"], data_dict["weapon"]):
        # if the weapon is already in the dictionary, add the amount to its existing value
        try:
            int(a)
        except ValueError: # if we have doubles with "undiclosed" amounts, just keep one of them
            weapon_amounts[w] = a
        else:
            if w in weapon_amounts:
                old_int = int(weapon_amounts[w])
                new_int = int(a)
                weapon_amounts[w] = str(old_int + new_int)
            else:
                # else just use existing value
                weapon_amounts[w] = a

    # clear old lists and add newly updates values
    amount.clear()
    weapon.clear()
    for w, a in weapon_amounts.items():
        amount.append(a)
        weapon.append(w)
    return amount, weapon

def set_dimensions(amount, weapon, df): # calculates the maximum length of columns and dataframe 
    max_length_local = max(len(amount), len(weapon), len(df))
    return max_length_local

def write_to_df_committed(amount, weapon, max_length): # creates a dictionary with all entries. those can then be appended to the dataframe
    global df_committed
    global date_index

    # create new column names based on the unique date
    column_1 = f"{all_website_dates[date_index]} Amount"
    column_2 = f"{all_website_dates[date_index]} Description"
    column_3 = f"{all_website_dates[date_index]} Last Occurrence [Dummy]" # gives "Yes"/"No" -> if "Yes", this was the last time this item is used, ie check if a new item got renamed in following entry
    column_4 = f"{all_website_dates[date_index]} New Item [Dummy]" # gives "Yes"/"No"
    column_5 = f"{all_website_dates[date_index]} Newly Committed" # substract the difference in newly delivered from total change to get new commitments
    column_6 = f"{all_website_dates[date_index]} Newly Delivered" # take value from delivered table
    column_7 = f"{all_website_dates[date_index]} Previous Commitment increased [Dummy]" # if deliveries are larger than commitments, we correct the previous entry in its "Amount" if 1, this dummy is just there to identify
    column_8 = f"{all_website_dates[date_index]} HUMAN CHECK" # marks all changes that are not in [0,1000] or where we match fuzzy (not exact) 
    column_9 = f"{all_website_dates[date_index]}" # visual seperator
    # create a dictionary to hold the new column values
    new_data = {}

    # fill the dictionary with the existing data from the DataFrame
    for col in df_committed.columns:
        new_data[col] = df_committed[col].tolist() + [""] * (max_length - len(df_committed[col]))
    
    # add the new lists to the dictionary
    new_data[column_1] = amount + [""] * (max_length - len(amount))
    new_data[column_2] = weapon + [""] * (max_length - len(weapon))
    new_data[column_3] = [""] * max_length
    new_data[column_4] = [""] * max_length
    new_data[column_5] = [""] * max_length
    new_data[column_6] = [""] * max_length
    new_data[column_7] = [""] * max_length
    new_data[column_8] = [""] * max_length
    new_data[column_9] = ["|"] * max_length

    df_committed = pd.DataFrame(new_data) # fill df with new entries
    if date_index > 0: # we need at least one entry to compare against 
        df_committed.apply(calculate_change_committed, axis=1, df_comm=df_committed)
    
    # reset date lists
    matched_indices_newly_delivered.clear() 
    matched_indices_newly_committed.clear()

    return df_committed

def write_to_df_delivered(amount, weapon, max_length):    
    global df_delivered
    global date_index
    column_1 = f"{all_website_dates[date_index]} Amount"
    column_2 = f"{all_website_dates[date_index]} Description"
    column_3 = f"{all_website_dates[date_index]} Last Occurrence [Dummy]"
    column_4 = f"{all_website_dates[date_index]} Change"
    column_5 = f"{all_website_dates[date_index]} New Item [Dummy]"
    column_6 = f"{all_website_dates[date_index]} HUMAN CHECK" # if fuzzy matching != 100% match or deviation negative or greater than (1000)
    column_7 = f"{all_website_dates[date_index]}" # visual seperator

    new_data = {}
    
    for col in df_delivered.columns:
        new_data[col] = df_delivered[col].tolist() + [""] * (max_length - len(df_delivered[col]))
    
    new_data[column_1] = amount + [""] * (max_length - len(amount))
    new_data[column_2] = weapon + [""] * (max_length - len(weapon))
    new_data[column_3] = [""] * max_length
    new_data[column_4] = [""] * max_length
    new_data[column_5] = [""] * max_length
    new_data[column_6] = [""] * max_length
    new_data[column_7] = ["|"] * max_length
    
    # update dataframe with new values
    df_delivered = pd.DataFrame(new_data) 
    
    # calculate changes from last to current website version
    if date_index > 0: # we need at least one entry to compare against 
        df_delivered.apply(calculate_change_delivered, axis=1, df_deli=df_delivered) # applies the function to each row in the delivered dataframe

    matched_indices_change_delivered.clear() # reset counter in the end

    return df_delivered

def unconcatenate(itemlist): # works for two elements concatenated with "and [digit]"

    weaponstotal = []
    for item in itemlist:
        doubles = re.search(r'and (\d+)', item) # if they list 2 entries with a "and" in one bullet, its always followed by a digit, hence look for that combi
        
        if doubles:
            # Split the item at the specific "and" with a number following it
            number = doubles.group(1) # save the number as I now cut it to only cut at the desired point
            parts = [re.split(r'and \d+', item)[0].strip(), number + re.split(r'and \d+', item)[1]] # add them back together in a list w/ number
            # Append individual parts to weaponstotal
            weaponstotal.extend(parts)
        else:
            weaponstotal.append(item)
    return weaponstotal # returns unconcatenated elements as list 

def million(input_str):
    # define a list to containing all possible variats of "million"
    millions = ["millions", "mil", "mio", "mio.", "mil.", "million"]
    
    # check if the first number is a digit, if yes, split into two parts
    if input_str[0].isdigit():
        words = input_str.split()
        # check for millions, then convert them to actual millions (e.g. 1.6 Mio -> 1600000)
        if words[1].lower() in millions:
            input_str_number = round(float(words[0].replace(",", "")) * 1000000)
            input_str_weapon = " ".join(words[2:]).strip()
        else:
            try:
                input_str_number = int(re.sub(r"(?<=\d)\.(?=\d)", "", words[0].replace(",", ""))) # gets rid of . and , in the amounts
            except ValueError:
                input_str_number = f"undisclosed {words[0]}" # if the first number is an int, but its not related to a number, eg "155mm ammunition" -> turns it to "undisclosed 155mm ammunition"
            input_str_weapon = " ".join(words[1:]).strip()
    else: # if there's no number associated with the weapon, label as "undisclosed"
        input_str_number = "undisclosed"
        input_str_weapon = input_str

    reformat_million = str(input_str_number) + " " + input_str_weapon

    return reformat_million

def scrapedate(x):
    url = "https://web.archive.org/web/"+x+"999999/https://www.bundesregierung.de/breg-en/news/military-support-ukraine-2054992"
    
    # scraping logic
    scrape = requests.get(url)
    soup = BeautifulSoup(scrape.text, "html.parser")
    
    dates = soup.findAll("span", class_="bpa-time")

    #define a list to extract the single one of the classes that has a weekday in it
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    global timeout
    #check if any of the days in weekdays appear in the list "dates" (there is always only one)
    for date in dates:
        date_text = date.get_text().strip() # strips away whitespaces
        matches = re.findall(r'\b(?:' + '|'.join(weekdays) + r')\b', date_text) # finds all (1) matching date from list dates in weekdays
        if matches:
            # returns date which is stripped of the day itself if the list. This way the list that will be the first entry in the csv is comma delimited
            timeout += 1
            time.sleep(15) # find the sweet spot for sleeping btw accessing url
            print(f"covered {timeout} days, currently at {x}")
            return date_text.replace("Monday, ","").replace("Tuesday, ","").replace("Wednesday, ","").replace("Thursday, ","").replace("Friday, ","").replace("Saturday, ","").replace("Sunday, ",""), url           

def scrape_list(y): # get html content to identify the line which contains committed/delivered, extract that line and split it in committed/delivered
              
    # get HTML content
    response = requests.get(y)
    html_content_full = response.text
    html_lines_full = html_content_full.splitlines()

    # Search for the line containing the string "handover"
    target_string = "handover"

    # enumerates until the lines variable reaches the word "handover", then saves the respective line as critical line
    for line_number, line in enumerate(html_lines_full, start=1):
        if target_string in line: #if not repeat the loop
            critical_line=line_number - 1 # to correctly retrieve the line in html code
            break #for efficiency to stop the loop once it found the word

    line_of_interest = html_lines_full[critical_line]

    # split the line of interest at cutoff point to get the substring containing delieveries [0] and committed [1]
    split_parts=line_of_interest.split("handover",1)

    delivered_string=split_parts[0]
    committed_string=split_parts[1]

    # do every action for both delivered and committed
    # search content within regular expression of li tags
    li_delivered = re.compile(r"<li>(.*?)</li>")
    matches_delivered = li_delivered.findall(delivered_string)

    li_committed = re.compile(r"<li>(.*?)</li>")
    matches_committed = li_committed.findall(committed_string)

    # clean strings of *, "more than ", bold tags, and "(before: ...) for better data consistency
    matches_delivered_clean = [match_delivered.replace("*","").replace("<strong>","").replace("</strong>","").replace("\xa0"," ").replace("“","").replace("”","").replace("more than ", "") for match_delivered in matches_delivered]
    matches_delivered_clean = unconcatenate(matches_delivered_clean) # ensures that all bullet points only contain single entries, if doubles occur, they get split
    for index, item in enumerate(matches_delivered_clean):
    # Search for the pattern " (before ...)" and substitute it with "" (more data cleaning)
        before_bracket = re.sub(r" \(before:.*?\)", "", item)
        if before_bracket:
            # if pattern is found, remove the (before: ...) bracket (allows for content to be still included after the bracket)
            matches_delivered_clean[index] = before_bracket.strip()

    # same for committed string
    matches_committed_clean = [match_committed.replace("*","").replace("<strong>","").replace("</strong>","").replace("\xa0"," ").replace("“","").replace("”","").replace("more than ", "") for match_committed in matches_committed]
    matches_committed_clean = unconcatenate(matches_committed_clean) 
    for index, item in enumerate(matches_committed_clean):
        before_bracket = re.sub(r" \(before:.*?\)", "", item)
        if before_bracket:
            matches_committed_clean[index] = before_bracket.strip()

    # update each individual entry so that it is split btw number of items and item description
    for i in range(len(matches_delivered_clean)):
        matches_delivered_clean[i] = million(matches_delivered_clean[i])

    # same for committed string
    for i in range(len(matches_committed_clean)):
        matches_committed_clean[i] = million(matches_committed_clean[i])

    amount_committed = []
    weapon_committed = []
    amount_delivered = []
    weapon_delivered = []
    
    # create 2 seperate lists, one for the amount and one for the weapon description
    for entry in matches_committed_clean:
        split_entry = entry.split(maxsplit=1)
        amount_committed.append(split_entry[0])
        weapon_committed.append(split_entry[1])
    for entry in matches_delivered_clean:
        split_entry = entry.split(maxsplit=1)
        amount_delivered.append(split_entry[0])
        weapon_delivered.append(split_entry[1])
    return amount_committed, weapon_committed, amount_delivered, weapon_delivered

def scrape_list_bpa(y):
    # Scraping logic
    scrape = requests.get(y)
    soup = BeautifulSoup(scrape.text, "html.parser")

    # Get the <div> part containing the richtext
    richtext = (soup.findAll(class_="bpa-richtext"))[-1]

    # Extract text from the richtext
    richtext_text = richtext.get_text()

    split_parts=richtext_text.split("handover", 1)

    delivered_list = (split_parts[0].split("•", 1)[1].split("Military")[0]).split("•")
    delivered_list = unconcatenate(delivered_list) # ensures that all bullet points only contain single entries, if doubles occur, they get split
    # same procedure as above
    committed_list = (split_parts[1].split("•", 1)[1].split("The total value of individual")[0]).split("•")
    committed_list = unconcatenate(committed_list) # same as above

    # remove the "*", "more than ", and the tab, then return values
    for i in range(len(delivered_list)):
        delivered_list[i] = delivered_list[i].replace("*", "").replace("more than ", "").strip()
        delivered_list[i] = million(delivered_list[i])
    
    for i in range(len(committed_list)):
        committed_list[i] = committed_list[i].replace("*", "").replace("more than ", "").strip()
        committed_list[i] = million(committed_list[i])
    
    # get rid of "(before: )" for better consistency
    for index, item in enumerate(committed_list):
        before_bracket = re.sub(r" \(before:.*?\)", "", item)
        if before_bracket:
            committed_list[index] = before_bracket.strip()

    for index, item in enumerate(delivered_list):
        before_bracket = re.sub(r" \(before:.*?\)", "", item)
        if before_bracket:
            delivered_list[index] = before_bracket.strip()

    amount_committed = []
    weapon_committed = []
    amount_delivered = []
    weapon_delivered = []
    
    # create 2 seperate lists, one for the amount and one for the weapon description
    for entry in committed_list:
        split_entry = entry.split(maxsplit=1)
        amount_committed.append(split_entry[0])
        weapon_committed.append(split_entry[1])
    for entry in delivered_list:
        split_entry = entry.split(maxsplit=1)
        amount_delivered.append(split_entry[0])
        weapon_delivered.append(split_entry[1])

    return amount_committed, weapon_committed, amount_delivered, weapon_delivered

def try_convert_to_int(value): # converts all int to int iff possible
    try:
        return int(value)
    except (ValueError, TypeError):
        return value
    
main()