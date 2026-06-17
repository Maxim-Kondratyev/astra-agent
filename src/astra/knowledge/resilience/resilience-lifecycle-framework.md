# AWS Resilience Lifecycle Framework

Source: https://docs.aws.amazon.com/prescriptive-guidance/latest/resilience-lifecycle-framework/

## Definition

AWS defines resilience as the ability of an application to resist or recover from
disruptions, including those related to infrastructure, dependent services,
misconfigurations, and transient network issues.

## Five Stages

### Stage 1: Set Objectives
- Define RTO (Recovery Time Objective) and RPO (Recovery Point Objective)
- Identify critical business functions and their availability requirements
- Document acceptable trade-offs between cost, complexity, and resilience

### Stage 2: Design and Implement
- Design for failure — assume components will fail
- Use Multi-AZ and multi-Region where appropriate
- Implement redundancy at every layer (compute, data, networking)
- Use managed services that provide built-in resilience
- Implement bulkhead patterns to limit blast radius

### Stage 3: Evaluate and Test
- Conduct failure mode analysis for each component
- Run chaos engineering experiments (AWS Fault Injection Service)
- Validate that recovery meets RTO/RPO targets
- Test failover procedures regularly (not just once)
- Use AWS Resilience Hub to assess resilience posture

### Stage 4: Operate
- Monitor key resilience metrics (availability, latency, error rates)
- Set alarms that trigger BEFORE customer impact
- Maintain runbooks for common failure scenarios
- Practice incident response regularly
- Track mean time to recovery (MTTR)

### Stage 5: Respond and Learn
- Conduct post-incident reviews (blameless)
- Update resilience objectives based on findings
- Feed learnings back into Stage 2 (design improvements)
- Share lessons across teams

## Maturity Levels

| Level | Description | Characteristics |
|-------|-------------|----------------|
| 1 — Reactive | No formal resilience practice | Single-AZ, no backups tested, manual recovery |
| 2 — Foundational | Basic resilience in place | Multi-AZ, automated backups, basic monitoring |
| 3 — Proactive | Continuous improvement | Chaos testing, automated failover, defined RTO/RPO |
| 4 — Advanced | Resilience as culture | Multi-Region, game days, resilience in CI/CD |

## Key Metrics to Assess

- Recovery Time Objective (RTO): How fast can you recover?
- Recovery Point Objective (RPO): How much data can you afford to lose?
- Mean Time to Recovery (MTTR): How fast do you actually recover?
- Availability: What % uptime do you achieve?
- Blast radius: How many customers are affected by a single failure?
