import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent  # sql agent
from langchain.sql_database import SQLDatabase
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import initialize_agent,AgentType
from sqlalchemy import create_engine ## sqlalchemy will help to map that data comes from the outside SQLDB
import sqlite3
from langchain_groq import ChatGroq
from urllib.parse import quote_plus  ## if you have special characters in password use quote_plus
import os

st.set_page_config(page_title="LangChain: Chat with Sql DB")
st.title("LangChain: Chat with Sql DB")

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

radio_opt=["Use the SQLLITE 3 Database","Connect My SQL Database"]
 
select_opt=st.sidebar.radio(label="Choose the DB which you want",options=radio_opt)

if radio_opt.index(select_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input("Provide MYSQL Host")
    mysql_user=st.sidebar.text_input("MYSQL user")
    mysql_password=st.sidebar.text_input("MYSQL password",type="password")
    mysql_db=st.sidebar.text_input("MySQL database")

else:
    db_uri=LOCALDB




api_key=st.sidebar.text_input("Enter your Groq API Key:",type="password")




if not db_uri:
    st.info("Please enter the database information and and uri")


if not api_key:
    st.warning("Please add the Groq API key")
    st.stop()

os.environ["GROQ_API_KEY"] = api_key 

llm=ChatGroq(groq_api_key=api_key,model_name="llama3-8b-8192",streaming=True)

@st.cache_resource(ttl="2h")

def configure_db(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"student.db").absolute()
        print(dbfilepath)
        creator=lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro",uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri==MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MYSQL connection details")
            
            st.stop()
        mysql_password_encoded = quote_plus(mysql_password)    
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password_encoded}@{mysql_host}/{mysql_db}"))
    
if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)

## toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)
agent=create_sql_agent(llm=llm,toolkit=toolkit,verbose=True,agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION)

if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"]=[{"role":"assistant","content":"How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query=st.chat_input(placeholder="Ask any question from the database")

if user_query:
    st.session_state["messages"].append({"role":"user","content":user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback=StreamlitCallbackHandler(st.container())
        response=agent.run(user_query,callbacks=[streamlit_callback])
        st.session_state.messages.append({"role":"assistant","content":response})
        st.write(response)
        