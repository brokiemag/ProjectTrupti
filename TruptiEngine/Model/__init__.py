

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import MessagesPlaceholder

from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

from langchain_core.runnables import RunnableParallel, RunnablePassthrough
import asyncio
import json

load_dotenv(override=True)

class ModelHandler:
    def __init__(self):
        self._google_api_key = os.getenv("GOOGLE_API_KEY")

        if not self._google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
        
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
        self.general_memory = None


    def persist_chat_init(self, system_prompt):
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("user", "{input}")
            ])
            print("Prompt variables:", prompt.input_variables)  # Debug check

            small_memory = ConversationBufferMemory(return_messages=True)
            conversation = ConversationChain(
                llm=self.llm,
                memory=small_memory,
                prompt=prompt,
                verbose=False
            )
            self.general_memory = small_memory

            return conversation, {}        
        except Exception as e: 
            return None, {"error": str(e)}

    def instant_chat(self, system_ctx, user_input):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_ctx}"),
                ("user", "{user_input}")
            ]
        )
        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({
            "system_ctx": system_ctx,
            "user_input": user_input
        })

        return response

    def create_chain(self, system_ctx, user_input):
        prompt = ChatPromptTemplate.from_messages(
        [
            ("system", f"{system_ctx}"),
            ("user", f"{user_input}")
        ]
        )
        chain = prompt | self.llm | StrOutputParser()
        return chain
    

