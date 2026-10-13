FROM python:3.11-slim

WORKDIR /usr/src/app

COPY . .

CMD ["python", "FoodAI.py"]

#docker build --no-cache -t inf1103-p12-g9 .

#docker run --rm inf1103-p12-g9 ls -la

#docker run --rm --network none inf1103-p12-g9 python logic_manager_testing.py     (to run the test script)

#docker run --rm -it -e GEMINI_API_KEY inf1103-p12-g9     (to run the container with the GEMINI_API_KEY environment variable set)