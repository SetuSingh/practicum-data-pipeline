### Problem 3: 

# **Building a Secure Data Pipeline with Data Change Monitoring and Access Controls**

**Mentor: [Declan Gowran](mailto:dgowran@integralads.com)**  
***Research Domain: Data Security, Access Control, Data Privacy, Data Monitoring Data Engineering*** 

# Project Overview

In this project, students will create a secure data pipeline that incorporates data security best practices. They will design and implement a system that monitors data changes, controls access to sensitive information, and ensures data integrity and compliance. This pipeline will enable students to apply security, monitoring, and access control measures effectively in a data engineering environment.

As the reliance on software and data increases, ensuring security in software creation and data engineering becomes paramount. One critical challenge is integrating secure programming practices throughout the software development lifecycle to prevent vulnerabilities, protect sensitive data, and ensure compliance with regulatory requirements. Additionally, with the growing use of cloud infrastructure, distributed systems, and big data, secure programming must scale effectively without compromising performance or flexibility.

In the domain of data engineering, this challenge expands to include the handling of large-scale data processing pipelines that might deal with sensitive data such as personally identifiable information (PII), financial data, or healthcare records. Developers must adopt practices that safeguard data at every stage, from ingestion to storage and processing, ensuring that sensitive information remains encrypted and access controls are strictly enforced. Secure data management not only requires robust encryption methods but also careful design of APIs, databases, and cloud resources to prevent unauthorized access or data breaches.

Moreover, with the rise of regulatory frameworks such as GDPR, HIPAA, and CCPA, companies must ensure that their software adheres to strict data privacy laws. Failing to comply with these standards can result in significant legal and financial consequences. Data encryption, tokenization, and anonymization techniques are essential to protect sensitive information and ensure compliance with these regulations.

In addition to encryption and access control, secure programming also involves mitigating common vulnerabilities such as SQL injection, cross-site scripting (XSS), and insecure deserialization, which are often exploited by attackers. 

### Problem Statement

With the increasing reliance on data pipelines, securing data at every stage of ingestion, processing, and storage is critical. Sensitive data such as personally identifiable information (PII), financial data, or health records must be protected from unauthorized access, tampering, and breaches. This project focuses on designing a data pipeline with:

1\. Data Security: Implement encryption and secure storage for sensitive information.  
2\. Data Change Monitoring: Detects and responds to unauthorized or unexpected changes in data.  
3\. Access Controls: Enforce fine-grained access policies to ensure that only authorized personnel or services can access sensitive data.

### Learning Objectives

By the end of the project, students will:  
\- Understand key principles in data security, including encryption, data integrity, and data privacy compliance.  
\- Implement mechanisms to detect changes in data and log modifications for auditing.  
\- Design role-based access control (RBAC) policies to manage data access securely.  
\- Gain hands-on experience with monitoring tools to track data integrity and access.

### Project Steps

### Step 1: Set Up Project Environment

1\. Platform Selection: Use Minikube (for Kubernetes) or Docker to simulate a local development environment.  
2\. Install Required Tools: Install Apache Kafka or Apache Airflow for data orchestration, Prometheus and Grafana for monitoring, and relevant libraries (e.g., Great Expectations for data quality checks).  
3\. Set Up Data Source: Choose a data source (e.g., a CSV dataset or a small database) containing sensitive information, such as PII, to simulate data processing.

### Step 2: Data Ingestion and Security Implementation

1\. Data Ingestion: Design a simple pipeline using tools like Apache Kafka or Apache Airflow to ingest data in batches or in real time.

2\. Data Encryption:  
   \- Use AES encryption for data at rest and TLS for data in transit.  
   \- Store encryption keys securely using a tool like HashiCorp Vault or AWS KMS.

### Step 3: Implement Data Change Monitoring

1\. Data Change Detection:  
   \- Set up hashing (e.g., MD5 or SHA256) to compute and store hashes for each data record.  
   \- At each ingestion, compare new hashes to existing ones to detect unauthorized changes.

2\. Metadata and Schema Monitoring:  
   \- Use Great Expectations to define expectations for schema and data types, flagging changes automatically.  
   \- Set metadata constraints like row count, column types, or expected ranges to detect and log anomalies.

3\. Anomaly Detection:  
   \- Integrate Prometheus to monitor and track metrics associated with data access and modifications.  
   \- Use Grafana for real-time dashboards that alert on any data anomalies or breaches, such as unexpected access or modification patterns.

### Step 4: Implement Role-Based Access Control (RBAC)

1\. Define Roles and Permissions:  
   \- Create roles (e.g., Data Engineer, Data Analyst, Security Auditor) with specific permissions for accessing and modifying data.

2\. Access Controls:  
   \- Use Kubernetes RBAC if using Minikube or configure access policies at the application level.  
   \- Enforce that only specific roles can access sensitive datasets or processing steps, implementing least privilege practices.  
3\. Audit and Logging:  
   \- Enable logging for all data access activities, capturing which roles accessed or modified data and when.  
   \- Set up a log aggregation tool (e.g., Elastic Stack or Fluentd) to manage logs, track access, and detect unauthorized attempts.

### Step 5: Real-Time Monitoring and Alerts

1\. Monitoring Setup:  
   \- Set up Prometheus to monitor the pipeline’s data sources, data access, and modifications in real time.  
   \- Configure Grafana dashboards to visualize data integrity and access patterns.

2\. Alerting:  
   \- Define alert thresholds for unauthorized access or unexpected data changes (e.g., unusual schema changes or data distribution anomalies).  
   \- Set up automated notifications (e.g., via email or Slack) for alert events, enabling real-time response.

### Step 6: Implement Compliance and Data Privacy Measures

1\. Data Anonymization:  
   \- Anonymize or tokenize PII in the dataset, using techniques like k-anonymity or generalization to protect sensitive information.

2\. Compliance Testing:  
   \- Ensure the pipeline complies with privacy regulations (e.g., GDPR, HIPAA) by applying pseudonymization or data masking where necessary.

### Step 7: Documentation and Report

1\. Documentation:  
   \- Provide detailed documentation on pipeline setup, security measures, data monitoring processes, and access control policies.

2\. Report:  
   \- Summarize key results, including successful data change detections, compliance achievements, and lessons learned in implementing access controls.

### Expected Outcomes

1\. Secure Data Pipeline: A data pipeline with built-in data encryption, access controls, and data monitoring for a secure data processing environment.  
2\. Data Change Monitoring and Alerting: Mechanisms to detect and alert for unauthorized data changes.  
3\. Access-Controlled Data Flow: A role-based access control system that ensures only authorized access to sensitive data.  
4\. Compliance Measures: A data handling approach that ensures sensitive data is anonymized and managed per regulatory requirements.  
5\. Documentation and Reporting: A comprehensive report that includes documentation on setup, results of change detection and access monitoring, and regulatory compliance strategies.

### Suggested Tools

\- Data Orchestration: Apache Kafka, Apache Airflow  
\- Monitoring: Prometheus, Grafana  
\- Security Tools: HashiCorp Vault, AWS KMS  
\- Access Control: Kubernetes RBAC, Elastic Stack  
\- Data Quality: Great Expectations  
\- Anonymization: ARX, tokenization tools

### 

### Evaluation Criteria

Each phase of the project will be evaluated based on the following criteria to ensure the technical soundness of implementations, effective data security, access controls, and adherence to data privacy regulations. **All project artifacts, including code, configurations, and documentation, should be hosted or provided in a public GitHub repository (or similar) for easy review and assessment.**

Project Setup and Environment Configuration (15%)

- Completeness of project setup in the repository, including CI/CD configurations and environment setup documentation.  
- Effective configuration of the local environment using Minikube or Docker, with proper tool installation (Apache Kafka, Apache Airflow, Prometheus, Grafana).  
- Demonstration of a data source setup (e.g., sample CSV dataset or database) containing sensitive data to simulate secure data processing.

Data Ingestion and Security Implementation (20%)

- Quality and clarity of code for setting up the data ingestion pipeline in GitHub, with real-time or batch data handling.  
- Application of AES encryption for data at rest and TLS for data in transit, with encrypted keys managed securely using HashiCorp Vault or AWS KMS.  
- Code documentation and examples demonstrating secure key management best practices.

Data Change Monitoring Implementation (20%)

- Configuration of hashing (e.g., MD5 or SHA256) for data records to monitor unauthorized changes, available in the repository.  
- Documentation and integration of Great Expectations for schema and data type monitoring, with data anomaly alerts.  
- Configuration files for Prometheus and Grafana monitoring, demonstrating real-time tracking of data access and modifications.

Role-Based Access Control (RBAC) Implementation (20%)

- Definition of role-based access controls (Data Engineer, Data Analyst, Security Auditor) in code with clear permissions for access and data modifications.  
- Access control policies implemented through Kubernetes RBAC or application-level configurations.  
- Repository includes logging configurations and setup files for log aggregation tools (e.g., Elastic Stack), tracking and detecting unauthorized access attempts.

Real-Time Monitoring and Alerting (15%)

- Prometheus and Grafana configuration files for real-time monitoring of data integrity and access control, available in the GitHub repository.  
- Grafana dashboards for visualizing access and modification patterns, with alert thresholds for unauthorized access.  
- Automated alert notifications for critical security incidents, with instructions in the repository for replication.

Compliance and Data Privacy Measures (10%)

- Implementation of data anonymization techniques (e.g., k-anonymity, tokenization) in code, ensuring sensitive data handling per GDPR or HIPAA.  
- Documentation of compliance verification steps to show that data privacy requirements are met.  
- Code and setup for pseudonymization or data masking techniques, preventing unauthorized access to PII.

## 

## Overall Scoring

*Grades will be based on students’ ability to set up and secure data pipelines, monitor changes, enforce access controls, and document compliance measures effectively. All relevant artifacts must be in a public GitHub repository (or equivalent), with comprehensive documentation for easy access and review. Evaluation will also consider the clarity and completeness of the documentation, change detection details, security configurations, and regulatory adherence.*