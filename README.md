# Problem Statement
## Context
### Business Scenario
Cycling strategy is major lever as we look at unlocking capacity or reducing inventory. We have different cycling tools example RLA, however it is difficult to implement as we are not considering the sequencing at the plant location 

## Project Details
### Objective
Incorporate sequencing constraints and ensure our cycling recommendations is implementable at the plant-line level 

### Approach
- Understand the plant- line and product information 
- Identifying the constraints for sequencing at plant level 
- Develop optimization model which looks at sequencing ideally at daily level for plant – line combination with objective function of either reducing inventory or increasing capacity 

## Expected Outcome
### Business Impact
- New Capability – Cycling & Sequencing tool
- Ensure we are able to recommend cycling  
- Opportunity to reduce inventory by 3-5% leveraging optimal cycling recommendations 

### Feasibility
- Develop algorithm to plan daily plant line combination to ensure either we increase capacity or reduce inventory 
- Scalable algorithm as it is similar to TDC model however at daily plant-line level 
- Potential to pick up one platform – Example Fruit snacks to pilot the model

### Challenge
- Computational power to model a daily plant line level model

### Idea Owner
Rahul Shah

### Author
Monojit Mandal

### Team Members
Monojit Mandal, Dhruv Thakral, Rahul Shah

### Extended Data Support Team
Harshit Gupta, Ankita Pamidigantam

# Solution
## Mathematical Formulation (MILP)

**Set**

$P:$ Set of products\
$T:$ Set of timeframes

**Parameters**

$COT_{p,q}$ : Changeover time between product p and q\
$SS_{p,t}$ : Safety stock of product p during timeframe t\
$LR_{p}$ : Line rate of product p\
$BINV_{p}$ : Beginning Inventory of product p\
$PC_{p}$ : Penalty cost of in case inventory is below safety stock for product p\
$IHC_{p,t}:$ : Inventory holding cost for product p per unit product per unit time\
$PM_{p}$ : Gross margin of product p\
$INVCAP_{p,t}$ : Inventory capacity (max DOS) of product p during time interval t\
$OC_{p,t}$ : Overflow cost of product p due to excess inventory over Inventory capacity (max DOS) during timeframe t

**Decision Variables**

$x_{p,t}\in \{0,1\}$ : 1 if product p is being produced during timeframe t else 0\
$w_{p,q,t}\in \{0,1\}$ : 1 if product p is changed over to product q after timeframe t else 0

**Auxiliary Variables**

$y_{p,t}^+\in \mathbb{R}^+$: Excess inventory level of product p above safety stock during after timeframe t\
$y_{p,t}^-\in \mathbb{R}^+$ : Inventory shortage of product p after timeframe t\
$of_{p,t}^+\in \mathbb{R}^+$:Inventory overflow (above max DOS) of product p after timeframe t\
$of_{p,t}^-\in \mathbb{R}^+$ : Inventory margin (below max DOS) of product p after timeframe t


**Objective Function**
$$min \sum_{p \in P} \sum_{q \in P} \sum_{t \in T} COT_{p,q}*w_{p,q,t}*LR_{p}*PM_{p}\ + \sum_{p \in P} \sum_{t \in T} \left( IHC_{p}*y_{p,t}^+\ +\ PC_{p}*y_{p,t}^-\ +\ OC_{p}*of_{p,t}^+ \right)$$

**Constraints**
- Logical relationship among decision and auxiliary variables:
$$x_{p,t}*x_{q,t+1} = w_{p,q,t}\ \forall p,q \in P; t \in T-----(1)$$
- Converting constraint 1 into linear constraints:
$$w_{p,q,t} \geq x_{p,t} + x_{q,t+1} - 1\ \forall p,q \in P; t \in T - \{T_{n}\}-----(1a)$$
$$w_{p,q,t} \leq x_{p,t}\ \forall p,q \in P; t \in T - \{T_{n}\}-----(1a)$$
$$w_{p,q,t} \leq x_{q,t+1}\ \forall p,q \in P; t \in T - \{T_{n}\}-----(1a)$$
- Only single product can be produced in a timeframe
$$\sum_{p \in P} x_{p,t} = 1-----(2)$$
- Relationship among production, inventory, demand, safety stock, overflow inventory:
$$\sum_{t \in T} x_{p,t}*LR_{p} + BINV_{p} - SS_{p} - \sum_{t \in T} D_{p,t} = y_{p,t}^+ + y_{p,t}^-\ \forall p \in P;t \in T-----(2)$$
$$\sum_{t \in T} x_{p,t}*LR_{p} + BINV_{p} - INVCAP_{p,t} - \sum_{t \in T} D_{p,t} =of_{p,t}^+ + of_{p,t}^-\ \forall p \in P;t \in T-----(2)$$