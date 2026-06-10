# ASTRA Architecture

## Overview

ASTRA is a **model-driven autonomous agent** that uses Claude Opus 4.8 (via Amazon Bedrock) to orchestrate read-only AWS API calls, analyse the results against best practices, and produce a scored assessment report.

The architecture follows the **agent-as-a-service** pattern: the agent runs inside the customer's AWS account, never sends data externally, and operates exclusively with read-only permissions.

## High-Level Architecture

```mermaid
graph TB
    subgraph Customer AWS Account
        subgraph Execution Layer
            Lambda[Lambda Function<br/>15-min timeout]
            IAM[IAM Role<br/>SecurityAudit + ReadOnlyAccess<br/>+ Explicit DENY mutations]
        end

        subgraph Agent Layer
            Agent[ASTRA Agent<br/>Strands SDK + Claude Opus 4.8]
            SecurityTools[Security Tools<br/>5 read-only checks]
            ResilienceTools[Resilience Tools<br/>5 read-only checks]
            SaaSTools[SaaS Tools<br/>5 read-only checks]
        end

        subgraph Data Sources
            SH[Security Hub]
            GD[GuardDuty]
            IAMService[IAM]
            S3[S3]
            EC2[EC2]
            RDS[RDS]
            ELB[ELB]
            R53[Route 53]
            ASG[Auto Scaling]
            Backup[AWS Backup]
            CW[CloudWatch]
            CE[Cost Explorer]
            Tagging[Resource Groups]
            Orgs[Organizations]
        end

        subgraph Output
            ReportBucket[S3 Report Bucket<br/>Encrypted, No Public Access]
            HTML[HTML Report]
            JSON[JSON Assessment]
        end

        Bedrock[Amazon Bedrock<br/>Claude Opus 4.8]
    end

    Lambda -->|assumes| IAM
    Lambda -->|runs| Agent
    Agent -->|reasoning| Bedrock
    Agent --> SecurityTools
    Agent --> ResilienceTools
    Agent --> SaaSTools
    SecurityTools --> SH & GD & IAMService & S3 & EC2
    ResilienceTools --> EC2 & RDS & ELB & R53 & ASG & Backup
    SaaSTools --> IAMService & S3 & CW & CE & Tagging & Orgs
    Agent -->|generates| HTML & JSON
    HTML & JSON -->|stored in| ReportBucket
```

## Agent Decision Flow

```mermaid
sequenceDiagram
    participant User
    participant Lambda
    participant Agent as ASTRA Agent
    participant Model as Claude Opus 4.8
    participant Tools as Assessment Tools
    participant AWS as AWS APIs

    User->>Lambda: Invoke (manual or scheduled)
    Lambda->>Agent: Start assessment
    Agent->>Model: System prompt + module selection
    
    loop For each tool (model-driven)
        Model-->>Agent: Call tool X
        Agent->>Tools: Execute tool X
        Tools->>AWS: Read-only API calls
        AWS-->>Tools: Response data
        Tools-->>Agent: Structured results
        Agent->>Model: Tool results
    end
    
    Model-->>Agent: Final assessment JSON
    Agent->>Lambda: Structured report
    Lambda->>Lambda: Generate HTML report
    Lambda->>Lambda: Save to S3
```

## Module Architecture

```mermaid
graph LR
    subgraph Security Module
        direction TB
        S1[Security Hub Findings]
        S2[GuardDuty Threats]
        S3[IAM Password Policy]
        S4[S3 Public Access]
        S5[Encryption at Rest]
    end

    subgraph Resilience Module
        direction TB
        R1[Multi-AZ Deployment]
        R2[Backup Coverage]
        R3[Auto Scaling Config]
        R4[Route53 Failover]
        R5[SPOF Detection]
    end

    subgraph SaaS Module
        direction TB
        T1[Tenant Isolation]
        T2[Resource Tagging]
        T3[Control Plane Separation]
        T4[Cost Allocation Tags]
        T5[Tenant Observability]
    end

    S1 & S2 & S3 & S4 & S5 --> Score1[Security Score]
    R1 & R2 & R3 & R4 & R5 --> Score2[Resilience Score]
    T1 & T2 & T3 & T4 & T5 --> Score3[SaaS Score]
    Score1 & Score2 & Score3 --> Overall[Overall Score 0-100]
```

## Security Model

```mermaid
graph TB
    subgraph Defence in Depth
        L1[Layer 1: IAM Policy<br/>SecurityAudit + ReadOnlyAccess]
        L2[Layer 2: Explicit DENY<br/>Blocks Create/Delete/Modify/Update/Terminate]
        L3[Layer 3: Code-level<br/>Only boto3 read calls in tool implementations]
        L4[Layer 4: No Internet<br/>VPC endpoints only — data never leaves account]
    end

    L1 --> L2 --> L3 --> L4

    style L1 fill:#fef3c7
    style L2 fill:#fecaca
    style L3 fill:#d1fae5
    style L4 fill:#dbeafe
```

## Deployment Topology

```mermaid
graph TB
    subgraph Customer Account
        VPC[VPC with Private Subnets]
        VPCe1[VPC Endpoint: Bedrock]
        VPCe2[VPC Endpoint: S3]
        LambdaVPC[Lambda in VPC<br/>No internet access]
        S3Bucket[Reports Bucket]
        Role[Read-Only IAM Role]
        
        VPC --> VPCe1 & VPCe2
        LambdaVPC --> VPCe1 & VPCe2
        LambdaVPC -->|writes reports| S3Bucket
        LambdaVPC -->|reads resources| Role
    end

    subgraph AWS Managed Services
        BedrockService[Amazon Bedrock<br/>us-east-1]
        S3Service[S3 Service]
    end

    VPCe1 -.->|private link| BedrockService
    VPCe2 -.->|private link| S3Service
```

## Data Flow

```mermaid
flowchart LR
    A[Trigger] -->|EventBridge<br/>or manual| B[Lambda]
    B --> C{Load modules}
    C -->|security| D[5 Security Tools]
    C -->|resilience| E[5 Resilience Tools]
    C -->|saas| F[5 SaaS Tools]
    D & E & F --> G[Claude Opus 4.8<br/>Bedrock]
    G --> H[Structured JSON<br/>Assessment]
    H --> I[HTML Report<br/>Generator]
    I --> J[S3 Bucket<br/>reports/YYYY-MM-DD/]
```

## Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Agent Framework | Strands Agents SDK | AWS-native, model-driven, minimal orchestration code |
| Foundation Model | Claude Opus 4.8 | Most capable reasoning for complex multi-service analysis |
| Compute | AWS Lambda | Serverless, no idle cost, 15-min sufficient for all modules |
| Deployment | AWS CDK (Python) | One-command deployment, parameterisable, reproducible |
| Storage | S3 (encrypted) | Customer-owned, no data leaves the account |
| Networking | VPC Endpoints | Zero internet egress, full data sovereignty |
| IAM | SecurityAudit + DENY policy | Defence-in-depth read-only enforcement |

## Scaling Considerations

| Dimension | Current Limit | Mitigation |
|-----------|--------------|------------|
| Lambda timeout | 15 minutes | Sufficient for 500+ resources across 3 modules |
| Bedrock throttling | Account-level quotas | Sequential tool calls (not parallel) to stay within limits |
| S3 bucket listing | 1000 objects per page | Paginated queries, sample up to 20 for efficiency |
| Multi-account | Single account per run | Organizations support planned (Phase 2) |
| Cost per run | ~$3-5 (Opus 4.8 tokens) | Can switch to Sonnet 4.6 for $0.50-1.00 per run |
