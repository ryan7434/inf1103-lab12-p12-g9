FROM python:3.11-slim

WORKDIR /usr/src/app

COPY . .

CMD ["python", "FoodAI.py"]

#build --no-cache -t inf1103-p12-g9 .
#docker run --rm inf1103-p12-g9 ls -la


#docker run -it --rm -e GEMINI_API_KEY=your_key_here -v "${PWD}:/usr/src/app" inf1103-p12-g9 python main.py