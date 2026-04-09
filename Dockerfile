# Using AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory to the Lambda task root
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install necessary packages
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy the Lambda function code to the container
COPY . .

# Set the handler to the Lambda function
CMD ["main.handler"]
