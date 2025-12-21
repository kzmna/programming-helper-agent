from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from config import Config

llm = ChatOpenAI(
            base_url=Config.OPENAI_API_BASE,
            api_key=Config.OPENAI_API_KEY,
            model=Config.MODEL_NAME,
            temperature=Config.TEMPERATURE,
        )

prompt = ChatPromptTemplate.from_messages([
        ("system", "Ты умный ассистент, отвечай кратко."),
        ("human", "Вопрос пользователя: {question}")
    ])

question = "Hello!"
formatted_messages = prompt.format_messages(question=question)

response = llm.invoke(formatted_messages)
print("GET LLM RESPONSE STATUS", response)