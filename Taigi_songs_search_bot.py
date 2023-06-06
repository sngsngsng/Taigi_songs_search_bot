"""
This is a Streamlit with Python script to search Taigi songs from dataframe. 
"""

# Import necessary libraries
import streamlit as st
#from PIL import Image
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
#dwn_url = '/local/.../Taigi_Songs_21000/Taigi_songs_21000_urls_clean.csv'

df = pd.read_csv(dwn_url)
#print(df.head(3))

#make URL	Song	Performer all string type
#if using cleaned version, no need to convert to string
df['URL'] = df['URL'].astype(str)
df['Song'] = df['Song'].astype(str)
df['Performer'] = df['Performer'].astype(str)


#Parse singer and/or song titles from a NLP sentences
#Parse singer and/or song titles from a NLP sentences

def set_search_method(sentence):
    ''' fĭlter out search method from sentence and do do some cleaning'''

    # remove all ending white spaces
    sentence = sentence.rstrip()

    # remove spaces between '.' and target strings
    # exact|fuzzy|included
    sentence = re.sub(r'[,|，|.|。|：|:]\s*(齊仝|大略|包括)', r'.\1', sentence)

    # set search method
    search_method = re.search(r'(齊仝|大略|包括)$', sentence)
    if search_method:
        sentence = re.sub(r'[,|，|.|。|：|:]\s*(齊仝|大略|包括)$', '', sentence)   #(?:\s|,|\.)
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
     
    #regulr expression patterns to filter keywords    
    patterns_list = [
        # the pattern with LESS placehoder should put in later position
        # pattern 例 = '共我揣1條龍千玉ê珍惜' / '共我揣龍千玉ê歌'
        [ r'(?:予我|揣||我欲愛|我欲聽|)(\d+)(?:條|塊|首|tiâu|tè|siú|\s)(.*?)(?:ê|\s|个)(.*?)$', {'performer': 2, 'song': 3, 'required_qty': 1 }],  
        # pattern 例 = '共我揣1條龍千玉' /  '共我揣1條珍惜'
        [ r'(?:予我|揣|我欲愛|我欲聽|)(\d+)(?:條|塊|首|tiâu|tè|siú|\s)(.*?)$', {'performer': 2, 'song': None, 'required_qty': 1 }], 
        # pattern 例 = '共我揣龍千玉ê珍惜'
        [ r'(?:予我|揣|我欲愛|我欲聽|)(.*?)(?:ê|\s|个)(.*?)$', {'performer': 1, 'song': 2, 'required_qty': None }], 
        # pattern 例 = '共我揣龍千玉' / '共我揣珍惜'
        [ r'(?:予我|揣|我欲愛|我欲聽)(.*?)$', {'performer': 1, 'song': None, 'required_qty': None }],
        # pattern 例 = '歌名有珍惜'
        [ r'歌名(.*?)$', {'performer': None, 'song': 1, 'required_qty': None }],
        # pattern 例 = '歌手龍千玉'
        [ r'(?:歌手|)(.*?)$', {'performer': 1, 'song': None, 'required_qty': None }],
    ]

    for ptn in patterns_list:
        pattern = re.compile( ptn[0] )
        mapping = ptn[1]
        match = pattern.search(sentence)

        if match != None:

            if mapping['performer'] != None:    
                result['performer'] = match.group(mapping['performer'])   #{ 'performer': '', 'song': '', 'required_qty': ''}
        
            if mapping['song'] != None:
                if match.group(mapping['song']) == '歌':
                    result['song'] = ''
                else:
                    result['song'] = match.group( mapping['song'] )
        
            if mapping['required_qty'] != None:
                result['required_qty'] = match.group( mapping['required_qty'])
            elif result['required_qty'] != 10000: # 10000 means '攏總|所有|全部'
                result['required_qty'] = default_required_qty   #default required_qty is 3

            break

    # if all values in result are empty
    if not any(result.values()):
        print('No setence pattern match found')
    #else:
    #    print(result.values())
    
    return result     #return a dictionary of re search result

# fuzzy search with performer and/or song titles

def fuzzy_search_url( df, keywords ): 
    # keywords is dictionary, same as previous result
    # fuzzy search with performer and/or song titles
    # get rows with fuzzy matching score of 'Performer' > 66 and 'Song' > 66

    search_method = keywords['search'] # 齊仝|大略|包括

    #initial two empty dataframes
    search_performer = pd.DataFrame()
    search_song = pd.DataFrame()

# keywords['performer']  keywords['song'] | 
# ----------------------|-----------------
#         Y             |        Y         | Exist
#         Y             |        N         | Exist, performer or Song in the same placeholder   
#         N             |        Y         | Not exist, parser would have set song = performer
#         N             |        N         | No match, return empty dataframe   

    if (keywords['performer']) == '' and (keywords['song']) == '':
    # if both performer and song are empty, return empty dataframe    
        print('Keywords are all empty, nothing to be searched.')
        #return empty dataframe
        return pd.DataFrame()

    if  (keywords['required_qty']) != '':
        default_qty = int(keywords['required_qty'])
    else:
        default_qty = 3

    #performer and Song share the same placeholder   
    if  ( keywords['performer'] ) != '' and ( keywords['song'] ) == '':
        if search_method == '包括':
            #get rows exactly match performer
            search_performer = df[df['Performer'].str.contains( keywords['performer'], na=False)]
            if search_performer.empty:
                print(f'No Performer {search_method} : ', keywords['performer'])
            search_song = df[df['Song'].str.contains(keywords['performer'], na=False)]
            if search_song.empty:
                print(f'No Song {search_method} : ', keywords['performer'])
            if not search_performer.empty or not search_song.empty:
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
 
    if  ( keywords['performer'] ) != '' and ( keywords['song'] ) != '':

        if search_method == '包括':
            search_performer = df[df['Performer'].str.contains(keywords['performer'], na=False)]
            search_song = search_performer[search_performer['Song'].str.contains(keywords['song'], na=False)]
            # clear search_performer
            search_performer = pd.DataFrame()        

            if search_song.empty:  
                print(f'No performer and song {search_method} : ', keywords['performer'] + '   ' + keywords['song'])
                #switch performer and song and search again
                print('Switch performer and song and search again')
                search_song = df[df['Song'].str.contains(keywords['performer'], na=False)]
                search_performer = search_song[search_song['Performer'].str.contains(keywords['song'], na=False)]
                # clear search_song
                search_song = pd.DataFrame() 
                if search_performer.empty:
                    print('Switch performer and song and match found')
                else:
                    print(f'No performer and song {search_method} : ', keywords['song'] + '   ' + keywords['performer'])
        
        elif search_method == '大略' or search_method == '齊仝':

            if search_method == '大略':
                fuzzy_threshold = 66

            elif search_method == '齊仝':
                fuzzy_threshold = 99

            search_performer = df[df['Performer'].apply(lambda x: fuzz.ratio(x, keywords['performer'])) > fuzzy_threshold]
            search_song = search_performer[search_performer['Song'].apply(lambda x: fuzz.ratio(x, keywords['song'])) > fuzzy_threshold]
            # clear search_performer
            search_performer = pd.DataFrame() 

            if search_song.empty:
                print(f'No performer and song {search_method} match : ', keywords['performer'] + '   ' + keywords['song'])
                #switch performer and song and search again
                print('Switch performer and song and search again')
                search_song = df[df['Song'].apply(lambda x: fuzz.ratio(x, keywords['performer'])) > fuzzy_threshold]
                search_performer = search_song[search_song['Performer'].apply(lambda x: fuzz.ratio(x, keywords['song'])) > fuzzy_threshold]
                # clear search_song
                search_song = pd.DataFrame()

                if search_performer.empty:
                    print('Switch performer and song and match found')
                else:
                    print(f'No performer and song {search_method} match : ', keywords['song'] + '   ' + keywords['performer'])

    #join two dataframes
    search_result = pd.concat([search_performer, search_song], ignore_index=True)

    #remove redunandt rows
    search_result = search_result.drop_duplicates(subset=['URL'], keep='first')
    
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

def help_text():
    text = '''      
                    * 若無講 beh 幾塊歌，預設揣 10 塊歌。（ 歌 ê 量詞用 塊／條／首 lóng 會用--tit。） 
                    
                    * 倒爿紅揤á 揤--loeh，進前 ê 物á 總á 總清挕捒。

                    * 幼路用法：

                        - 揣龍千玉ê歌，攏總
                        - 我欲愛所有沈文程
                        - 予我全部珍惜
                    (揣 tio̍h 幾條歌，攏總 hō͘ 你。用 攏總|所有|全部 lóng 會用--tit ）

                        - 我欲聽回心轉意, 大略
                        - 我欲愛海岸, 大略
                    (用 Fuzzy Algorith 來揣，拍字小可重tâⁿ mā 盡量合看覓。)       

                        - 我欲愛珍惜, 齊仝
                        - 揣阿吉仔ê相思, 齊仝
                    (揣 歌手 ia̍h-sī 歌名 chham 你拍 ê 字完全相仝--ê hō͘ 你。)       

                        - 歌名相思, 包括
                        - 歌手吉仔, 包括
                    (這是預設--ê，你免 koh 拍。
                     揣 歌手 ia̍h-sī 歌名 包括 你拍 ê 字--ê hō͘ 你。)      


                    * 這支 Web App koh leh 改良, 
                    機能 chham ĭnterface mā 會調整 hō͘ koh 較媠--leh，
                    lia̍h-chún 欲反應問題／bug ia̍h-sī 交流，指導，
                    來 [台語講科技／Tâi-gí káng kho-ki](https://www.facebook.com/groups/274434021656256) FB 面冊社團 交流--1-ē， 
                    逐家鬥陣用台語來講科技，
                    用科技來耍台語，助台語。 '''
    return text

st.set_page_config( page_title='揣台語歌／Chhōe Tâi-gí kóa', layout='centered' )

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
    input_text = st.text_input("", st.session_state["input"], key="input", 
                            # Place holder of input area   
                            placeholder="共我揣洪榮宏ê莫傷阮的心 / 我欲愛3條董事長ê歌 /  拍 'help' 看 koh 較 chē 說明" , 
                            on_change=clear_text,    
                            label_visibility='hidden')
    input_text = st.session_state["temp"]
    return input_text

def Taigi_songs_search(input):
    
    output_text = []

    if  input.strip().lower() == 'help':
        output_text.append( help_text() )
        return output_text

    result = re_pattern_match( input )
    df_result = fuzzy_search_url( df, result )

    if df_result.empty:
        #output_text.append('--------------------------------')
        output_text.append('無揣--著-neh, 改--一下 koh 試看覓。')
        return output_text

    qty = len(df_result)

    #append the result to a string
    output_text.append( f'-- 咱揣--tio̍h {qty} 塊來聽--1-ē, 無講幾塊 tio̍h 先 10 塊。' )

    idx = 0

    for index, row in df_result.iterrows():
        
        if qty == 1 and idx == 0:
            output_text.append( f'- 孤塊 [{idx+1}/{qty}]')
        elif qty > 1 and idx == 0:
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

# Define function to search again
#the funciton is still faulty now
#def search_again():

#    output = Taigi_songs_search(input=st.session_state["temp"])  

#    st.session_state.past.append(user_input)  
#    st.session_state.generated.append(output)  

#    return

# Define function to clear output text
def clear_output():
    """
    Clears output text, but preserving the last one.
    """    
    st.session_state["generated"] = []
    st.session_state["past"] = []
    st.session_state["input"] = ""
    st.session_state["temp"] = ""

    return

# Sidebar informations
with st.sidebar:
    st.markdown('''有閒 mā 來 [台語講科技／Tâi-gí káng kho-ki](https://www.facebook.com/groups/274434021656256) FB 面冊社團 交流--1-ē : 
              ==> 用台語來講科技，用科技來耍台語，助台語''') 

    st.markdown('''這 ê Web App 資料 ùi chia 來--ê，感恩，咱搜揣 soah mā 是 koh 用網鍊 連--轉去看歌詞佮影片 
                ==> [台語歌真正正字歌詞網](https://www.facebook.com/groups/922800454445724) ''')
 
     #Add a button to search again with the same conditions
     #the function is still faulty now
#    st.sidebar.button("仝條件 hoh 揣--1-改", on_click = search_again, type='primary')

    #Add a button to clear output
    st.sidebar.button("清清--leh", on_click = clear_output, type='primary')
        
    st.markdown( '''* 拍 'help' 看 koh較 chē 說明 ''') 
    st.markdown( '''
        按怎用：
        - 我欲聽龍千玉ê望你回心轉意
        - 揣3塊龍千玉ê歌 
        - 予我5條沈文程
        - 予我20塊珍惜
        - 我欲愛羅時豐
        - 我欲愛珍惜
        - 揣阿吉仔ê相思
        - 歌名相思
        - 歌手阿吉仔
        - 蕭煌奇 相思海岸
       '''
            ) 

# Set up the Streamlit app layout
st.title("揣台語歌 ／ Chhōe Tâi-gí koa")
#st.subheader("")
st.write("Ùi chia 拍字。。。")
   
#Add a button to start a new chat
#st.sidebar.button("Koh 揣看覓", on_click = clear_search, type='primary')

# Get the user input
user_input = get_text()
output_area = st.empty()

# Generate the output using the ConversationChain object and the user input, and add the input/output to the session
if user_input:
    output_area.empty()
    output = Taigi_songs_search(input=user_input)  
    st.session_state.past.append(user_input)  
    st.session_state.generated.append(output)  

# Allow to download as well
download_str = []

# Display the serarch result, and allow the user to download it

# Output the generated text
with output_area.container():
    generated_text = ''
    for i in range(len(st.session_state['generated'])-1, -1, -1):
        for j in range(0, len(st.session_state["generated"][i])):
            generated_text += st.session_state["generated"][i][j] + '\n'
            #download_str.append(st.session_state["generated"][i][j])
        generated_text += '\n'
        #download_str.append('\n')
    st.write(generated_text)
    
# end of the code
