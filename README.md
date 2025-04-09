# Simple Pipeline for loading CSV data to AWS RDS MySQL

## Description
This repo describes a data pipeline for a CSV file data to be automatically loaded to AWS RDS MySQL database. The CSV file can originate from a producer external to the company or can be a source internal to the company. This pipeline utilizes the "Event notification" feature of S3 bucket to trigger a Lambda function.

## Diagram
![Loading data to RDS](https://github.com/user-attachments/assets/04769ede-0fe4-44f8-837e-fb000ad77233)

## Reading the diagram <a name="my-custom-anchor-point"></a>
1. In the above illustration we can see that there are more than one way how a CSV file can land-up in an AWS S3 bucket of Data Engineering team.
2. Using S3 Event Notification for S3 bucket ("-raw" in this case), an AWS Lambda function can be triggered to carry on the further tasks.
3. same as 4
4. Lambda function creates a Secrets Manager client session and retrieves secrets like the RDS DB credential username, password, host url, port number etc., using "**get_secret_value**" method of **boto3** library.
5. Lambda function uses S3 **boto3** client to interact with S3 and uses "**get_object**" method to get the csv file data. This data is then used to create a pandas DataFrame using "**read_csv**" method of **pandas** library.
6. Lambda function makes use of "**to_sql**" method in **pandas** to write records stored in the DataFrame to a RDS MySQL database. It uses the **SQLAlchemy** engine to make a connection to the database.
7. Based on the response received from the AWS RDS database, the lambda function comes to know whether the dataload was successful or not.
8. Lambda function then utilzes the SNS **boto3** client to "**publish**" the appropriate notification (Success or Failure) to the specific SNS topic.
9. Once the CSV file processing is complete, the CSV file would be moved to "-archive" bucket. If not moved, then optionally it can be moved to less expensive S3 storage classes and eventually moved to S3 Glacier.

All the relevant teams and members who have subscribed to that SNS topic would receive the notification. Then all the authentic consumers can then consume this data available in the RDS database.

## This is a demo project, i encourage you to try out creating one by your own. I have tried to summaries the steps in the following section.

* Note: Steps on how to move the file to "archive" bucket has not been included in the following section. You can research and try out that on your own.

### Pre-requisites

Before you begin, make sure you have:
* An AWS account
* Basic understanding of the following:
	* AWS services like
 		* S3
   * Lambda
   * RDS
   * Secrets Manager
   * SNS
   * STS

### Step 1

Create two AWS S3 buckets, for example:
* s3://dehlive-sales-_<your_AWS_Account_number>_-us-east-1-**raw**
* s3://dehlive-sales-_<your_AWS_Account_number>_-us-east-1-**archive**

### Step 2

Creating a free tier AWS RDS Database (MySQL Engine):

Keep all options to default, but for the below values.
  * Engine options: MySQL
  * Templates: Free tier
  * DB instance identifier: _eg: database-1_
  * Master username: _<set appropriate username>_
  * Master password: _<set appropriate password>_ 
  * Select lowest available instance type: db.t3.micro
  * Public access: Yes
  * VPC security group (firewall): Create new
  * New VPC security group name: _eg: demo-rds-mysql-security-group_
  * Additional configuration
	   * Initial database name: _eg: salesdb_prod_
	   * Enable automated backups: deselect this (we don’t want automated backups for demo)
	   * Enable encryption: deselect this (we don’t want to encrypt the demo instance)
	   * Auto minor version upgrade: deselect this (we don’t want to enable this for demo)
  * Create the database by clicking on the “Create database” button.

Review the created database.

Review the newly created security group:
If the permission is not as follows, update the security group to allow inbound traffic from Anywhere

![image](https://github.com/user-attachments/assets/de556b90-02dc-407e-8449-7c3e3735815e)

### Step 3

Connect to the newly created Database Engine using “MySQL Workbench” or “DBeaver”.

![image](https://github.com/user-attachments/assets/5cc9aba0-287d-4f81-9532-d42a8f6a5de4)


Based on the column and datatype, create the table “sales” the database “salesdb_prod”. 

![image](https://github.com/user-attachments/assets/e610babf-e365-4a7f-8df3-8403bad2478e)


### Step 4

Create Secrets in Secret Manager: 

* Click on “Store a new secret”.
* Keep all options to default, but for the below values.
* Secret type: Credentials for Amazon RDS database
* User name: _<Username set during database-1 creation>_
* Password:  _<Password set during database-1 creation>_
* Database: select the database we are interested in i.e. “database-1”
* Click on “Next”.
* Secret name: give an appropriate name to this secret. This name would be provided in the Lambda function later on.
* Click on “Next”.
* Again click on “Next”.
* Review the details and click on “Store”. 

The newly stored secret will appear in the “Secrets” list. Review the details by clicking on the Secret name. 

On the next page, in the “Overview” tab → click on the “Retrieve secret value” button. Review whether all the secrets are saved correctly or not. 

During the Lambda execution, we would be requiring the table name as well. Hence we need to add table details to this secret dictionary. 
* Click on the “Edit” button.
* “Edit secret value” page will pop-up.
* Click on the “Plaintext” tab. At the end of the Dictionary, add another key-value pair for "table":"sales".  

![image](https://github.com/user-attachments/assets/1f1263e3-81da-401b-af46-d9806785c2b2)


### Step 5

Create a SNS topic, subscribe an email to that topic to get the notification emails as per the Lambda execution status. 

 
### Step 6

Create an IAM role for Lambda function.

![image](https://github.com/user-attachments/assets/5c9efbaa-36a0-4ea7-a138-b0dcb5282111)


### Step 7

Create a Lambda function to carry out all the tasks mentioned in the [Reading the diagram](#my-custom-anchor-point) section.

  * Function name: give an appropriate name to this lambda function 
  * Runtime: latest or appropriate previous version of Python 
  * Change default execution role: 
      * Execution role: Use an existing role. Select the role created in the above step. 
  * Then click on the “Create Function” button. 

![image](https://github.com/user-attachments/assets/a8dddc30-4c63-4246-8e87-c2ce37866498)

Reference python code is present in this repo by the name "s3_to_rds.py"

Check the Handler name:
![image](https://github.com/user-attachments/assets/0cc08b55-4b2d-49b5-a9bc-80fe3cd439ac)

Add layers for following libraries:
* pandas
* SQLAlchemy
* sql-connector-python

![image](https://github.com/user-attachments/assets/c53e1d05-43b9-4a8f-875d-f047559e5487)


### Step 8

To add triggers to S3 bucket.

![image](https://github.com/user-attachments/assets/9e637165-3e69-49b7-86eb-8175502d4d50)

![image](https://github.com/user-attachments/assets/30667cf7-4d84-4061-927f-735114a71cdd)

Rest all options can be left unchecked, as it is.

![image](https://github.com/user-attachments/assets/a24c2ced-4603-4ac1-9510-3082badc94c4)

Click on the “Save changes” button. 


### Step 9

Test the pipeline by uploading a data file to the “-raw” bucket. 

https://github.com/user-attachments/assets/ce1b7755-4571-4a41-80b6-503082dc832b



 

Now the data in RDS is ready to be queried by consumers like Data Analysts, Data Scientists, Visualization tools like Tableau, PowerBI etc, Report creation applications etc. 


### Sample Notification email:

#### Notification sample #1: Failure

![image](https://github.com/user-attachments/assets/274353dc-3bef-40d7-8659-98c2a7dfb5ca)

#### Notification sample #2: Failure

![image](https://github.com/user-attachments/assets/9b29c2b3-06b1-4a23-9749-234697d77e78)

#### Notification sample #1: Success

![image](https://github.com/user-attachments/assets/795f6031-2135-435c-acc8-a197e9796dde)


### Sample CloudWatch Logs:

CloudWatch Logs for the Lambda execution come handy when you want to troubleshoot any error in the code. For example:

#### Log sample #1: Failure

![image](https://github.com/user-attachments/assets/1b54d88b-b297-4ba2-b11f-880af6e219d1)

#### Log sample #1: Success

![image](https://github.com/user-attachments/assets/b11dc95c-a8b0-43b7-9f05-31000215c6d5)


## In case of any suggestions, corrections or queries

Please reach out to me at er.alhad.khade@gmail.com. 

Thank you. 

Keep learning and keep sharing!!!


❤️
