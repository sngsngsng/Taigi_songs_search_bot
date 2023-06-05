"""
This is a Streamlit with Python script to search Taigi songs from dataframe. 
"""

# Import necessary libraries
import streamlit as st
from PIL import Image
import pandas as pd
import re
from fuzzywuzzy import fuzz

############################################################################################
### Taigi songs searchinig part
############################################################################################

#reading public csv from google drive
# df from google drive
#url='https://drive.google.com/file/d/1UnaqvjzaCG2K-wZiy_f4-0nUc85DKtMq/view?usp=sharing'  #Taigi_songs_21000_urls_1_1000.csv
url='https://drive.google.com/file/d/1Uu2Y-XU5lCjP3VJ9bt56yBwUGkhEEDH6/view?usp=sharing'  #Taigi_songs_21000_urls.csv

file_id=url.split('/')[-2]
dwn_url = 'https://drive.google.com/uc?id=' + file_id

#df from local
#dwn_url = '/home/martin/TG/scraping/Taigi_Songs_21000/Taigi_songs_21000_urls_clean.csv'

df = pd.read_csv(dwn_url)
#print(df.head(3))

#make URL	Song	Performer all string type
#if using cleaned version, no need to convert to string
df['URL'] = df['URL'].astype(str)
df['Song'] = df['Song'].astype(str)
df['Performer'] = df['Performer'].astype(str)


#Parse singer and/or song titles from a NLP sentences
def set_search_method(sentence):
    ''' fĭlter out search method from sentence and do do some cleaning'''

    # remove all ending white spaces
    sentence = sentence.rstrip()

    # remove spaces between '.' and target strings
    # exact|fuzzy|included
    sentence = re.sub(r'(?:\s|,|\.)\s*(齊仝|大略|包括)', r'.\1', sentence)

    # set search method
    search_method = re.search(r'(齊仝|大略|包括)$', sentence)
    if search_method:
        sentence = re.sub(r'(?:\s|,|\.)\s*(齊仝|大略|包括)$', '', sentence) 
        search_method = search_method.group(1)
    else:
        search_method = '包括' # default search method if not specified

    # remove all ending white spaces
    sentence = sentence.rstrip()

    return sentence, search_method

# sentence match and parse
def re_pattern_match( sentence ):
    '''match and parse sentence with regular expression patterns'''

    sentence, search_method = set_search_method(sentence)

    print(sentence, search_method)

    result = { 'performer': '', 'song': '', 'required_qty': '', 'search' : search_method } #search_method: 'exact', 'fuzzy' or 'included'

    default_required_qty = 10 

    # if there is any one of 攏總|所有|全部, set result['required_qty'] = 10000 and then remove them
    # else set result['required_qty'] = ''

    pattern = re.compile( r'(攏總|所有|全部)' )
    match = pattern.search(sentence)
    if match != None:
        sentence = re.sub(r'(攏總|所有|全部)', '', sentence)
        print('Will list all items actually found.')
        result['required_qty'] = 10000 # this will be over-ridden by required_qty set in the following patterns
    
    #remove half-width and full-width ','， '.'，'：' in the sentence
    sentence = re.sub(r'[,|，|.|。|：|:]', '', sentence)

    #remove all heading and ending white spaces
    sentence = sentence.strip()

    patterns_list = [
        # the pattern with LESS placehoder should put in later position
        # pattern 例 = '共我揣1條龍千玉ê珍惜' / '共我揣龍千玉ê歌'
        [ r'(?:予我|揣|搜揣|共我揣|我欲愛|揣予我|)(\d+)(?:條|塊|首|tiâu|tè|siú|\s)(.*?)(?:ê|\s|个|的)(.*?)$', {'performer': 2, 'song': 3, 'required_qty': 1 }],  
        # pattern 例 = '共我揣1條龍千玉' /  '共我揣1條珍惜'
        [ r'(?:予我|揣|搜揣|共我揣|我欲愛|揣予我|)(\d+)(?:條|塊|首|tiâu|tè|siú|\s)(.*?)$', {'performer': 2, 'song': None, 'required_qty': 1 }], 
        # pattern 例 = '共我揣龍千玉ê珍惜'
        [ r'(?:予我|揣|搜揣|共我揣|我欲愛|揣予我|)(.*?)(?:ê|\s|个|的)(.*?)$', {'performer': 1, 'song': 2, 'required_qty': None }], 
        # pattern 例 = '共我揣龍千玉' / '共我揣珍惜'
        [ r'(?:予我|揣|搜揣|共我揣|我欲愛|揣予我|)(.*?)$', {'performer': 1, 'song': None, 'required_qty': None }],
    ]

    for ptn in patterns_list:
        pattern = re.compile( ptn[0] )
        mapping = ptn[1]
        match = pattern.search(sentence)

        if match != None:

            result['performer'] = match.group(mapping['performer'])   #{ 'performer': '', 'song': '', 'required_qty': ''}
        
            if mapping['song'] != None:
                if match.group(mapping['song']) == '歌':
                    result['song'] = ''
                else:
                    result['song'] = match.group( mapping['song'] )
        
            if mapping['required_qty'] != None:
                result['required_qty'] = match.group( mapping['required_qty'])
            elif result['required_qty'] != 10000: # 10000 means '攏總|所有|全部'
                result['required_qty'] = default_required_qty  #default required_qty

            break

    # if all values in result are empty
    if not any(result.values()):
        print('No setence pattern match found')
    #else:
    #    print(result.values())
    
    return result     #return a dictionary of re search result


def fuzzy_search_url( df, keywords ): 
    # keywords is dictionary, same as previous result
    # fuzzy search with performer and/or song titles
    # get rows with fuzzy matching score of 'Performer' > 66 and 'Song' > 66

    search_method = keywords['search'] # 齊仝|大略|包括

    #initial two empty dataframes
    search_performer = pd.DataFrame()
    search_song = pd.DataFrame()

    if (keywords['performer']) == '' and (keywords['song']) == '':
        print('Keywords are all empty, nothing to be searched.')
        #return empty dataframe
        return pd.DataFrame()

    if  (keywords['required_qty']) != '':
        default_qty = int(keywords['required_qty'])
    else:
        default_qty = 3

    if  ( keywords['performer'] ) != '' and ( keywords['song'] ) == '':
        if search_method == '包括':
            #get rows exactly match performer
            search_performer = df[df['Performer'].str.contains( keywords['performer'], na=False)]
            if search_performer.empty:
                print(f'No Performer {search_method} : ', keywords['performer'])
                search_song = df[df['Song'].str.contains(keywords['performer'], na=False)]
                if search_song.empty:
                    print(f'No Song {search_method} : ', keywords['performer'])
                else:
                    print(f'Song {search_method} : ', keywords['performer'])
        
        elif search_method == '大略' or search_method == '齊仝':

            if search_method == '大略':
                fuzzy_threshold = 66

            elif search_method == '齊仝':
                fuzzy_threshold = 99

            search_performer = df[df['Performer'].apply(lambda x: fuzz.ratio(x, keywords['performer'])) > fuzzy_threshold]     
            if search_performer.empty:    
                print(f'No Performer {search_method} match : ', keywords['performer'])
                search_song = df[df['Song'].apply(lambda x: fuzz.ratio(x, keywords['performer'])) > fuzzy_threshold]
                if search_song.empty:
                    print(f'No Song {search_method} match : ', keywords['performer'])
                else:
                    print(f'Song {search_method} match : ', keywords['performer'])
        
        #join two dataframes
        search_result = pd.concat([search_performer, search_song], ignore_index=True)

        #remove redunandt rows
        search_result = search_result.drop_duplicates(subset=['URL'], keep='first')
 
    if  (keywords['song']) != '' :
        if search_method == '包括':
            search_song = df[df['Song'].str.contains(keywords['song'], na=False)]
            print('song after search', search_song)
            search_performer = search_song[search_song['Performer'].str.contains(keywords['performer'], na=False)]
            print('performer after search', search_performer)
            if search_performer.empty:  
                print(f'No Performer and Song {search_method} : ', keywords['performer'] + '  ' + keywords['song'] )
            else:
                print(f'Performer and Song {search_method} : ', keywords['performer'] + '  ' + keywords['song'] )
        
        elif search_method == '大略' or search_method == '齊仝':

            if search_method == '大略':
                fuzzy_threshold = 66

            elif search_method == '齊仝':
                fuzzy_threshold = 99

            search_song = df[df['Song'].apply(lambda x: fuzz.ratio(x, keywords['song'])) > fuzzy_threshold]
            search_performer = search_song[search_song['Performer'].apply(lambda x: fuzz.ratio(x, keywords['performer'])) > fuzzy_threshold]        
            if search_performer.empty:
                print(f'No performer and song {search_method} match : ', keywords['performer'] + '  ' + keywords['song'] )
            else:
                print(f'Performer and Song {search_method} match : ', keywords['performer'] + '  ' + keywords['song'] )
    
        # only the identical items in both dataframes
        search_result = search_performer
    
    available_qty = min(default_qty, len(search_result))

    if default_qty == 10000: # 10000 means '攏總|所有|全部'
        print(f'default_qty = 攏總, but actually available_qty = {available_qty} ' )

    search_result = search_result.sample( available_qty ) # random sample rows from search_result of available_qty

    #print(' Fuzzy search result: \n', fuzzy_search_result)

    if search_result.empty:
        print(f'No matching on search_method = {search_method}, return empty dataframe.')
    else:
        print(len(search_result), ' items found on search_method = ', search_method)    

    return search_result
############################################################################################
### Streamlit part
############################################################################################

#@st.cache(allow_output_mutation=True)

# Set Streamlit page configuration
st.set_page_config( page_title=' Taigi songs search', layout='centered' )

# Initialize session states
if "generated" not in st.session_state:
    st.session_state["generated"] = []
if "past" not in st.session_state:
    st.session_state["past"] = []
if "input" not in st.session_state:
    st.session_state["input"] = ""
if "temp" not in st.session_state:
    st.session_state["temp"] = ""

def clear_text():
    st.session_state["temp"] = st.session_state["input"]
    st.session_state["input"] = ""

# Define function to get user input
def get_text():
    """
    Get the user input text.
    """
    input_text = st.text_input("You: ", st.session_state["input"], key="input", 
                            placeholder="輸入你想欲揣ê歌手 and/or 歌名...", 
                            on_change=clear_text,    
                            label_visibility='hidden')
    input_text = st.session_state["temp"]
    return input_text

def Taigi_songs_search(input):
    
    result = re_pattern_match( input )
    df_result = fuzzy_search_url( df, result )

    output_text = []

    if df_result.empty:
        output_text.append('無揣--著-neh, 改--一下 koh 試看覓。')
        return output_text

    qty = len(df_result)

    #append the result to a string
    output_text.append( f'咱揣著：{qty} 塊歌.' )

    idx = 0

    for index, row in df_result.iterrows():
        
        if qty > 1 and idx == 0:
            output_text.append( f'- 頭塊 [{idx+1}/{qty}]')
        elif qty > 1 and idx == qty-1:
            output_text.append( f'- 尾塊 [{idx+1}/{qty}]')
        else:
            output_text.append( f'- 第 {idx+1} 塊 [{idx+1}/{qty}]')

        output_text.append( f'歌手 : {row["Performer"]}') 
        output_text.append( f'歌名 : {row["Song"]}')
        output_text.append(f'網鍊 : {row["URL"]}')   
        idx += 1   
    
    return output_text  

    # Define function to start a new chat
def clear_search():
    """
    Clears output text, but preserving the last one.
    """    
    st.session_state["generated"] = []
    st.session_state["past"] = []
    st.session_state["input"] = ""

with st.sidebar:
    st.markdown("---")
    st.markdown(">>>")
    st.markdown(
       "揣台語歌 ／ Chhōe Tâi-gí koa"
            )

# Set up the Streamlit app layout
st.title("揣台語歌 ／ Chhōe Tâi-gí koa")
#st.subheader("")

        
#Add a button to start a new chat
st.sidebar.button("Koh 揣看覓", on_click = clear_search, type='primary')

# Get the user input
user_input = get_text()

# Generate the output using the ConversationChain object and the user input, and add the input/output to the session
if user_input:
    output = Taigi_songs_search(input=user_input)  
    st.session_state.past.append(user_input)  
    st.session_state.generated.append(output)  

# Allow to download as well
download_str = []

# Display the serarch result, and allow the user to download it

generated_text = ''

#for i in range(len(st.session_state['generated'])-1, -1, -1):
#    generated_text += st.session_state["generated"][i]+'/n'
#    generated_text += st.session_state["past"][i]+'/n'

for i in range(len(st.session_state['generated'])-1, -1, -1):
    st.write(st.session_state["past"][i] )
    for j in range(0, len(st.session_state["generated"][i])):
        st.write(st.session_state["generated"][i][j] )
                            
# end ------------------------------

