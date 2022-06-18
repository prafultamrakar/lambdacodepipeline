from __future__ import print_function
from boto3.session import Session
#this is my comment
import json

import boto3
import tempfile
import botocore
import traceback

print('Loading function')

code_pipeline = boto3.client('codepipeline')
step_functions = boto3.client('stepfunctions')


def put_job_success(job, message):
    """Notify CodePipeline of a successful job
    
    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status
        
    Raises:
        Exception: Any exception thrown by .put_job_success_result()
    
    """
    print('Putting job success')
    print(message)
    code_pipeline.put_job_success_result(jobId=job)
  
def put_job_failure(job, message):
    """Notify CodePipeline of a failed job
    
    Args:
        job: The CodePipeline job ID
        message: A message to be logged relating to the job status
        
    Raises:
        Exception: Any exception thrown by .put_job_failure_result()
    
    """
    print('Putting job failure')
    print(message)
    code_pipeline.put_job_failure_result(jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})
 
def continue_job_later(job, message):
    """Notify CodePipeline of a continuing job
    
    This will cause CodePipeline to invoke the function again with the
    supplied continuation token.
    
    Args:
        job: The JobID
        message: A message to be logged relating to the job status
        continuation_token: The continuation token
        
    Raises:
        Exception: Any exception thrown by .put_job_success_result()
    
    """
    
    # Use the continuation token to keep track of any job execution state
    # This data will be available when a new job is scheduled to continue the current execution
    continuation_token = json.dumps({'previous_job_id': job})
    
    print('Putting job continuation')
    print(message)
    code_pipeline.put_job_success_result(jobId=job, continuationToken=continuation_token)



def check_stepfunction_status(job_id, stateMachineARN):
    """Monitor an already-running StateMachine update/create
    
    Succeeds, fails or continues the job depending on the StateMachine status.
    
    Args:
        job_id: The CodePipeline job ID
        stateMachine: The stateMachine to monitor
    
    """
    
    state_machine_list_executions = step_functions.list_executions(
        stateMachineArn=stateMachineARN,statusFilter='RUNNING',maxResults=1)
    length_of_executions = len(state_machine_list_executions['executions'])
    print("No of Executions Running: "+str(length_of_executions))
    
    if (length_of_executions == 1):
        print("Your Step function is Currently executing previous job so, send Continuation token")
        continue_job_later(job_id, 'Stepfunction Execution still in progress')
        
    elif (length_of_executions == 0):
        """
        No Stepfunction job is running
        
        """
        put_job_success(job_id, 'Stepfunction Execution complete')
        
    else:
        # a failed result.
        put_job_failure(job_id, 'Update failed, Since No of Executions is > 1 i.e: ' + str(length_of_executions))



def get_user_params(job_data):
    """
    Decodes the JSON user parameters and validates the required properties.
    
    Args:
        job_data: The job data structure containing the UserParameters string which should be a valid JSON structure
        
    Returns:
        The JSON parameters decoded as a dictionary.
        
    Raises:
        Exception: The JSON can't be decoded or a property is missing.
        
    """
    try:
        # Get the user parameters which contain the StepFunctionARN and Cloudwatch Event
        user_parameters = job_data['actionConfiguration']['configuration']['UserParameters']
        decoded_parameters = json.loads(user_parameters)
    except Exception as e:
        # We're expecting the user parameters to be encoded as JSON
        # so we can pass multiple values. If the JSON can't be decoded
        # then fail the job with a helpful message.
        raise Exception('UserParameters could not be decoded as JSON')
    
    if 'stateMachineARN' not in decoded_parameters:
        # Validate that the stateMachineARN is provided, otherwise fail the job
        # with a helpful message.
        raise Exception('Your UserParameters JSON must include the stateMachineARN')
    
    return decoded_parameters

def lambda_handler(event, context):
    """The Lambda function handler
    
    If a continuing job then checks the StepMachine status
    and updates the job accordingly.
    
    
    Args:
        event: The event passed by Lambda
        context: The context passed by Lambda
        
    """
    try:
        
        """
        Code to Disable CloudWatch Event for Triggering Stepfunction is 
        """
        
        # Extract the Job ID
        job_id = event['CodePipeline.job']['id']
        
        # Extract the Job Data 
        job_data = event['CodePipeline.job']['data']
        
        params = get_user_params(job_data)
        
        # Get the list of artifacts passed to the function
        # artifacts = job_data['inputArtifacts']
        
        stateMachineARN = params['stateMachineARN']
        
        print("State Machine ARN: " + stateMachineARN)
        
        if 'continuationToken' in job_data:
            # If we're continuing then the create/update has already been triggered
            # we just need to check if it has finished.
            check_stepfunction_status(job_id, stateMachineARN)
        else:
            # we just need to check if it has finished.
            check_stepfunction_status(job_id, stateMachineARN) 
        

    except Exception as e:
        # If any other exceptions which we didn't expect are raised
        # then fail the job and log the exception message.
        print('Function failed due to exception.') 
        print(e)
      
    
    print('Function complete.') 
    return "Complete."
