# A Comprehensive Analysis of Benchmark Instances for the Vehicle Routing Problem and its Variants

## An Introduction to VRP Benchmarking: The Foundation for Algorithmic Evaluation

### The VRP as an NP-Hard Challenge

The Vehicle Routing Problem (VRP), formally introduced by Dantzig and Ramser in 1959, stands as a cornerstone of combinatorial optimization and operations research.1 In its canonical form, the VRP seeks to determine the optimal set of routes for a fleet of vehicles, originating from one or more depots, to serve a geographically dispersed set of customers.3 As a generalization of the well-known Traveling Salesman Problem (TSP), the VRP inherits its computational complexity and is classified as NP-hard, meaning that finding a provably optimal solution becomes computationally intractable as the problem size increases.4 This intractability poses a significant scientific challenge, as the VRP lies at the heart of countless real-world logistics and transportation systems. The stakes are substantial; even marginal improvements in routing efficiency can yield significant savings, often in the range of 5% to 20% of total transportation costs, making the VRP a problem of immense practical and economic importance.1

The core VRP has spawned a multitude of variants, each incorporating additional constraints to better model the nuances of real-world operations. These include the Capacitated VRP (CVRP), which limits vehicle load; the VRP with Time Windows (VRPTW), which imposes service time intervals for customers; the VRP with Pickup and Delivery (VRPPD), where goods are moved between customer locations rather than just from a depot; and the Multi-Depot VRP (MDVRP), among many others.3 Each additional constraint layer further complicates the problem, often exponentially increasing the size and complexity of the solution space.

### The Indispensable Role of Standardized Benchmarks

For NP-hard problems like the VRP and its variants, where exact optimization methods are often impractical for large, real-world instances, the development and evaluation of heuristic and metaheuristic algorithms become paramount.4 These algorithms—such as Genetic Algorithms, Tabu Search, Simulated Annealing, and Ant Colony Optimization—aim to find high-quality, near-optimal solutions within a reasonable computational time frame.4 However, assessing the relative performance of these diverse and often stochastic methods would be impossible without a common frame of reference. This is the indispensable role of standardized benchmark instances.

Benchmark sets provide a curated and universally accessible collection of problem instances that serve as the bedrock for rigorous scientific comparison and progress.10 They allow researchers to test new algorithms against established problems where the characteristics are well-understood and the best-known solutions (BKS), and in some cases, the proven optimal solutions (OPT), have been documented through decades of collective research effort.4 The evolution of these benchmarks reflects the parallel evolution of computational power and algorithmic sophistication. Early instances were small and designed to be solved to optimality, whereas modern benchmarks have grown to include thousands of customers, deliberately pushing the boundaries of what is computationally feasible and ensuring a continued need for advanced heuristic development.7 The structure of these benchmarks is not merely a random collection of problems; it is a carefully designed landscape that reflects the research community's evolving understanding of the problem's core challenges and the industry's demand for solutions to increasingly complex logistical puzzles.

### The Hierarchical Objective: A Common Evaluation Paradigm

A critical concept for interpreting and comparing results across many modern VRP benchmarks is the hierarchical objective function. While the classical VRP objective is often to minimize a single metric, such as total distance traveled, many contemporary benchmarks, particularly those involving time windows or multiple vehicles, employ a lexicographical or hierarchical optimization goal.15 The most common hierarchy is:

1. **Primary Objective:** Minimize the number of vehicles used.
    
2. **Secondary Objective:** Minimize the total travel distance (or time).
    

This two-tiered objective is prevalent in the widely used Solomon and Gehring & Homberger VRPTW benchmarks, as well as the Li & Lim PDPTW instances.16 This structure is not an academic abstraction; it mirrors real-world business priorities where capital expenditures (the cost of acquiring and maintaining vehicles) are often considered more critical to minimize than variable operational costs (fuel and labor associated with distance).19 An algorithm is thus judged first on its ability to find a solution with the minimum possible fleet size and only then on the efficiency of the routes it designs for that fleet. This is a crucial distinction, as results obtained using a hierarchical objective are not directly comparable to those from algorithms that optimize a monolithic, weighted-sum objective (e.g., total distance plus a large penalty for each vehicle used).17 Researchers must be cognizant of the specific objective function used by a benchmark set to ensure valid comparisons and accurately assess an algorithm's performance.

## The CVRPLIB Collection: A Consolidated Repository for the Capacitated VRP

### Overview of CVRPLIB

CVRPLIB stands as the authoritative, centralized library for benchmark instances of the Capacitated Vehicle Routing Problem (CVRP).4 Its primary function is to consolidate and standardize instances from a wide array of seminal publications, providing a single point of access for the research community.7 The fundamental problem addressed by these instances is the CVRP, where a fleet of homogeneous vehicles with a fixed capacity, denoted by

Q, must serve a set of customers with known demands, starting and ending their routes at a single depot.2 The primary objective is to minimize the total distance traveled while respecting the capacity constraints of the vehicles. Some instances may also impose a maximum route duration.15

### Analysis of Foundational Benchmark Sets (Within CVRPLIB)

The power of CVRPLIB lies not in its homogeneity, but in its structured heterogeneity. The instances are not a monolithic block of "CVRP problems" but are grouped into distinct sets, each typically named after the authors who introduced them. These sets were often designed with specific research goals in mind, creating different types of challenges that test various aspects of an algorithm's capabilities.

- **Sets A, B, and P (Augerat, 1995):** These three sets are primarily differentiated by the geographical distribution of their customer locations, a crucial factor that heavily influences routing strategy.7
    
    - **Set A** instances feature customer coordinates generated randomly within a square. This tests an algorithm's general-purpose routing capability in an unstructured environment.
        
    - **Set B** instances feature clustered customer locations. These problems are designed to test an algorithm's ability to recognize and exploit spatial structure, often rewarding "cluster-first, route-second" logic.
        
    - **Set P** instances are modified versions of other problems, often with demands and vehicle capacities adjusted to create different levels of constraint tightness.
        
- **Sets E, F, and M (Christofides, Eilon, Fisher, Toth):** These represent some ofthe earliest and most influential benchmark instances in the VRP literature.7 The variations
    
    _within_ these sets are more straightforward than in Augerat's sets and are primarily based on scale and resource parameters.12 The key differentiators between instances like
    
    `E-n76-k7` and `E-n101-k8` are:
    
    - **Number of customers (n):** Testing the scalability of the algorithm.
        
    - **Number of available vehicles (K):** Influencing the partitioning of customers into routes.
        
    - **Vehicle capacity (Q) and demand distribution:** Creating varying levels of "tightness" in the capacity constraint. An instance where total demand is close to total vehicle capacity is generally harder than one with ample excess capacity.
        
- **Sets from Golden, Li, and Uchoa et al.:** This group of benchmarks marks a deliberate and significant escalation in problem size and complexity, representing a continuous "arms race" between algorithmic development and problem difficulty.7 As computational power grew and exact solvers became capable of solving the older, smaller instances, researchers created these new sets to ensure the problem remained challenging and a fertile ground for heuristic research. Their primary characteristic is
    
    **scale**, with customer counts ranging from 240 to over 1,000.7 For many of these instances, the optimal solution is not known, and the "Opt" column in CVRPLIB shows "no".12 Consequently, they serve as the primary proving ground for modern metaheuristics, where performance is measured by the quality of the solution (the Upper Bound, or UB) found within a reasonable time, rather than by proving optimality.4
    

### Data Structure and Access

CVRPLIB provides instances in a standardized text format, typically with a `.vrp` extension, and the corresponding best-known solutions in a `.sol` file.24 The CVRPLIB website presents a clear tabular organization for each benchmark set, providing essential information at a glance 12:

- **Instance:** The unique name of the problem (e.g., `A-n32-k5`).
    
- **_n_**: The number of customers.
    
- **_K_**: The number of vehicles.
    
- **_Q_**: The capacity of each vehicle.
    
- **UB:** The cost of the best-known solution (Upper Bound).
    
- **Opt:** A flag ("yes" or "no") indicating if the UB is proven to be optimal.
    
- **Features:** A set of icons providing links to download the instance file, the solution file, and a plot visualizing the customer and depot locations.
    

This structured presentation allows researchers to quickly identify and select instances based on their specific needs, whether it be problem size, spatial structure, or the availability of a proven optimal solution for verification.

Table 2.1: Characteristics of Major Benchmark Sets within CVRPLIB

| Author(s) & Year | Set Name(s) | Range of n (Customers) | Key Differentiating Feature(s) Within the Set |

| :--- | :--- | :--- | :--- |

| Christofides, Eilon (1969); Christofides, Mingozzi, Toth (1979); Fisher (1994) | E, F, M | 21 - 199 | Number of customers (n), vehicle capacity (Q), and maximum route length. Tests fundamental scalability and constraint handling. |

| Augerat (1995) | A, B, P | 31 - 79 | Spatial Distribution: Set A (random), Set B (clustered), Set P (modified). Tests ability to handle different geographical structures. |

| Golden et al. (1998) | Golden | 240 - 483 | Large Scale: Significantly larger than previous sets. Most instances are not solved to optimality. |

| Li et al. (2005) | Li | 560 - 1200 | Very Large Scale: Pushes the boundary of heuristic performance on massive instances. No optimal solutions are known. |

| Uchoa et al. (2014) | Uchoa, X | 100 - 1000 | Modern & Diverse: Generated to be challenging for state-of-the-art methods, with varying demand distributions and capacity tightness. |

## Solomon's Landmark VRPTW Instances: A Deep Dive into R, C, and RC Classes

### The Solomon Benchmark: A Paradigm for Structured Evaluation

The 56 benchmark instances for the Vehicle Routing Problem with Time Windows (VRPTW) introduced by Marius Solomon in 1987 are arguably the most influential and enduring in the entire VRP literature.7 For decades, they have served as the canonical testbed for nearly every significant VRPTW algorithm, from early constructive heuristics to modern deep reinforcement learning models.10 Their longevity stems not from their size—all instances are fixed at 100 customers—but from their brilliant and highly structured experimental design.7 Solomon did not create a mere collection of problems; he engineered a diagnostic tool designed to systematically probe the capabilities and weaknesses of routing and scheduling algorithms under a variety of controlled conditions.25

### The Core Differentiators: A 3x2 Experimental Design

The genius of the Solomon benchmark lies in its organization into six distinct classes, formed by the orthogonal combination of two primary factors: the geographical distribution of customers and the length of the scheduling horizon. This 3x2 design creates six unique problem types, each posing a different kind of challenge.

#### Factor 1: Geographical Distribution of Customers

This factor controls the spatial nature of the problem, testing an algorithm's routing and clustering capabilities.26

- **Class R (Random):** In instances R101–R112 and R201–R211, customer locations are generated from a uniform random distribution across a 2D plane. These instances lack any exploitable geographical structure, forcing an algorithm to rely on its pure routing and scheduling prowess. They test the core efficiency of insertion and improvement heuristics in an unstructured environment.
    
- **Class C (Clustered):** In instances C101–C109 and C201–C208, customers are grouped into distinct geographical clusters. These problems are explicitly designed to see if an algorithm can identify and exploit this structure. Effective algorithms will naturally create routes that serve customers within a single cluster before moving to another, minimizing long-distance travel between individual customers. They test an algorithm's ability to perform local optimization effectively.
    
- **Class RC (Random-Clustered):** In instances RC101–RC108 and RC201–RC208, the customer set is a hybrid, containing both randomly distributed points and distinct clusters. These instances are often considered the most difficult because they defy a single, monolithic strategy. An algorithm must be flexible enough to form dense, cluster-based routes while also efficiently weaving in the outlying random customers.
    

#### Factor 2: Scheduling Horizon and Customer Density per Route

This factor controls the temporal and capacity-related nature of the problem, testing an algorithm's scheduling and packing capabilities.26

- **Series 1 (Classes R1, C1, RC1):** These instances are defined by a _short scheduling horizon_ and relatively tight vehicle capacity. The depot's time window is narrow, and the total route time is constrained. This combination severely limits the number of customers that can be serviced by a single vehicle. As a result, the problem becomes dominated by **scheduling**. The primary challenge is not finding the most efficient route, but finding a _feasible_ route at all that satisfies all time windows. The number of vehicles required is high, and the routes are short.
    
- **Series 2 (Classes R2, C2, RC2):** These instances are defined by a _long scheduling horizon_ and a large vehicle capacity. The depot's time window is wide, allowing for a full day of operation. This permits a single vehicle to serve many customers. Here, the problem is dominated by **routing and packing**. The challenge shifts from finding feasibility to finding the most efficient way to combine a large number of customers into a few long routes, much like a classical CVRP.
    

The interplay of these two factors creates a powerful analytical framework. An algorithm's performance profile across these six classes is highly revealing. For instance, an algorithm that excels on C1 instances but performs poorly on R1 instances demonstrates strong local clustering ability but weak global routing logic. Conversely, an algorithm that performs well on R2 but poorly on R1 is adept at packing many customers into a route but struggles when faced with tight, complex temporal constraints. This diagnostic capability is the core reason for the benchmark's enduring relevance.

### The Nuance of Time Windows

Beyond the main 3x2 structure, further variation exists _within_ each of the six classes. The instances (e.g., R101 vs. R102 vs. R103) are differentiated by the properties of their customer time windows. According to the generation methodology, the percentage of customers with time windows varies (25%, 50%, 75%, or 100%), as does the width (tightness) of those windows.26 This creates a gradient of temporal difficulty even within a single class, allowing for a fine-grained analysis of how an algorithm responds to increasing levels of scheduling pressure.

Table 3.1: The 3x2 Experimental Design of Solomon's VRPTW Benchmark

| Geographical Distribution | Series 1 (Short Horizon, Few Customers/Route) | Series 2 (Long Horizon, Many Customers/Route) |

| :--- | :--- | :--- |

| R (Random) | Class R1: Randomly located customers with tight scheduling constraints. Demands high feasibility-finding capability and efficient handling of temporal constraints. | Class R2: Randomly located customers with loose scheduling constraints. Demands efficient routing and packing of many customers into long routes. |

| C (Clustered) | Class C1: Geographically clustered customers with tight scheduling constraints. Tests ability to form feasible, dense routes within clusters under high temporal pressure. | Class C2: Geographically clustered customers with loose scheduling constraints. Tests ability to efficiently route within and between clusters on long, high-capacity routes. |

| RC (Random-Clustered) | Class RC1: Hybrid of random and clustered customers with tight scheduling constraints. Often the most difficult, requiring flexible strategies to manage both structures under temporal pressure. | Class RC2: Hybrid of random and clustered customers with loose scheduling constraints. Requires a balance of efficient packing within clusters and incorporating outlier customers into long routes. |

## Scaling Up: The Gehring & Homberger and Other Large-Scale VRPTW Extensions

### The Need for Larger Instances

While the 100-customer Solomon instances provide a masterful framework for analyzing the structural performance of algorithms, the relentless advance of computational power and the increasing scale of real-world logistics operations created a demand for larger, more challenging benchmarks.7 By the late 1990s, the VRP research community recognized the need for instances that would test the

_scalability and computational efficiency_ of their methods on problems more representative of industrial applications.14 An algorithm that performs well on 100 customers may not be practical if its runtime grows exponentially, rendering it useless for a 500-customer problem.

### Gehring & Homberger's Extended Benchmark

The most prominent response to this need came from Gehring and Homberger, who in 1999 introduced a set of large-scale VRPTW instances.7 These benchmarks are not a conceptual departure from Solomon's work but rather a direct and deliberate extension of it. They were generated using the same underlying principles, preserving the critical R, C, and RC classification for geographical distribution and the Series 1 and 2 distinction for scheduling horizon and customer density.28

The primary difference, and the sole purpose of their creation, is **scale**. The Gehring & Homberger sets contain instances with 200, 400, 600, 800, and 1000 customers.17 The instance naming convention clearly reflects this lineage. For example, an instance named

`c1_10_1` represents a 1000-customer problem (`_10_`) that belongs to the **C1** class—that is, it features clustered customers and a short scheduling horizon, just like its 100-customer counterparts in the Solomon set.28

The variations _within_ each size category (e.g., between different 400-customer instances) are also inherited from the Solomon generation methodology, involving different random seeds for location generation and variations in time window tightness and density. The objective function remains the same hierarchical goal: first, minimize the number of vehicles, and second, minimize the total distance.28

The introduction of these instances effectively created a new axis for algorithmic evaluation. While the Solomon set tests an algorithm's ability to handle different problem _structures_, the Gehring & Homberger set tests its ability to handle different problem _sizes_. An algorithm's performance degradation when moving from a Solomon instance (e.g., `C101`) to its larger Gehring & Homberger counterpart (e.g., `c1_2_1` for 200 customers) is a direct measure of its algorithmic complexity and scaling properties. This is a crucial evaluation for modern heuristics, particularly those employing computationally intensive techniques like large neighborhood search or population-based metaheuristics, where efficiency is as important as effectiveness.

## Introducing Paired Demands: The Li & Lim PDPTW Instances

### The Pickup and Delivery Problem with Time Windows (PDPTW)

The Pickup and Delivery Problem with Time Windows (PDPTW) represents a significant leap in complexity from the standard VRPTW. In the VRPTW, all goods flow from a central depot to customers (a one-to-many problem). In the PDPTW, goods are transported between specific origin-destination pairs of locations, creating a many-to-many problem structure.29 This introduces two critical new sets of constraints that fundamentally alter the nature of the routing problem 30:

1. **Pairing Constraint:** Each pickup location is uniquely paired with a delivery location. The same vehicle that performs the pickup must also perform the corresponding delivery.
    
2. **Precedence Constraint:** For any given pair, the visit to the pickup location must occur before the visit to the delivery location within the vehicle's route.
    

These constraints dramatically complicate the solution space. A simple neighborhood move, such as swapping two customers in a route, which might be valid in a VRPTW, could easily violate precedence in a PDPTW. Furthermore, the vehicle's load is no longer monotonically decreasing; it increases at pickup locations and decreases at delivery locations, requiring more complex capacity tracking.31

### Li & Lim Benchmark: Layering Complexity on a Known Foundation

To create a standardized testbed for this more complex problem, Li and Lim developed a set of PDPTW benchmark instances. In a methodologically sound approach similar to that of Gehring & Homberger, they did not create their instances from scratch. Instead, they derived them from the well-understood Solomon VRPTW instances.21 This design choice is crucial because it allows researchers to isolate the specific algorithmic challenges introduced by the pickup and delivery constraints.

The Li & Lim instances adopt the same geographical distributions as Solomon, resulting in three parallel classes 34:

- **`lc` instances:** Based on Solomon's **C (Clustered)** problems.
    
- **`lr` instances:** Based on Solomon's **R (Random)** problems.
    
- **`lrc` instances:** Based on Solomon's **RC (Random-Clustered)** problems.
    

They also inherit the Series 1 (short horizon) and Series 2 (long horizon) characteristics. The instances are grouped by the number of _tasks_, with sets for 100, 200, 400, 600, 800, and 1000 tasks.18 Since each transportation request consists of one pickup task and one delivery task, a 100-task instance corresponds to 50 pickup-and-delivery requests.

This direct lineage provides a powerful analytical tool. If a heuristic performs well on Solomon's `R101` instance but poorly on Li & Lim's corresponding `lr101` instance, the performance degradation can be attributed directly to the algorithm's inefficiency in handling the added precedence and pairing constraints, rather than its ability to manage random customer locations or tight time windows.

### Data Format and the Pairing Mechanism

A precise understanding of the Li & Lim data format is essential for any researcher wishing to implement a solver. The format is a clear, space-delimited text file where each line corresponds to a single location (either the depot, a pickup, or a delivery).37

The first line of the file specifies global parameters: the number of vehicles and the vehicle capacity. Subsequent lines detail each location with nine columns of data.

Table 5.1: The Li & Lim PDPTW Instance Data Format

| Column | Field Name | Description | Example (Pickup i, Delivery j) |

| :--- | :--- | :--- | :--- |

| 1 | Customer Index | Unique integer identifier for the location. | Line for i: i, Line for j: j |

| 2 | X-Coordinate | The X-coordinate of the location in a 2D plane. | x_i, x_j |

| 3 | Y-Coordinate | The Y-coordinate of the location in a 2D plane. | y_i, y_j |

| 4 | Demand | Quantity of goods. Positive for pickup, negative for delivery. | Line for i: +q, Line for j: -q |

| 5 | Earliest Arrival | The start of the service time window. | e_i, e_j |

| 6 | Latest Arrival | The end of the service time window. | l_i, l_j |

| 7 | Service Time | The time required to perform the service at the location. | s_i, s_j |

| 8 | Pickup Sibling | Index of the corresponding pickup location. Is 0 for a pickup. | Line for i: 0, Line for j: i |

| 9 | Delivery Sibling | Index of the corresponding delivery location. Is 0 for a delivery. | Line for i: j, Line for j: 0 |

The key to the pairing mechanism lies in columns 8 and 9. A location is identified as a pickup if its "Pickup Sibling" value is 0; its corresponding delivery location's index is then found in the "Delivery Sibling" column. Conversely, a location is a delivery if its "Delivery Sibling" value is 0, and its partner pickup is identified in the "Pickup Sibling" column.37 This explicit linking, combined with the positive/negative demand convention, provides an unambiguous representation of the paired requests that algorithms must satisfy.

## The Cordeau et al. Instances for Multi-Depot and Pickup-Delivery Problems

### Analyzing the `pr` Benchmark Set

The set of instances commonly referred to as `pr01` through `pr20` are a staple in the literature for testing algorithms on complex, multi-attribute VRPs. While the user's example link points to a page for "Capacitated VRP with Pick-up and Deliveries and Time Windows" (VRPPDTW) that lists these files, their origin lies in earlier work on the Multi-Depot Vehicle Routing Problem (MDVRP).38 These instances were introduced by Cordeau, Gendreau, and Laporte and have proven so versatile that they have been adapted and used to test a variety of problems, including MDVRP with Time Windows (MDVRPTW) and VRPPDTW.39 Their durability stems from a design that systematically varies multiple constraint types simultaneously.

### Key Differentiating Parameters within the `pr` Set

The differences between individual instances within the `pr` set (e.g., `pr01` vs. `pr02`, or `pr01` vs. `pr11`) are multi-faceted, creating a rich testbed for algorithmic robustness. The primary levers of difficulty are time window tightness, vehicle availability, and problem scale.

- **Time Window Tightness:** This is the most significant structural differentiator within the set. The 20 instances are explicitly divided into two groups based on the nature of their time windows.41
    
    - **Instances `pr01`–`pr10`:** This group is characterized by **tight and highly restrictive time windows**. The feasible time interval for service at each customer is narrow. This makes the problem heavily dominated by feasibility-seeking. The search space is highly non-convex and fragmented, meaning that simple changes to a route are very likely to render it infeasible.42 Algorithms must employ sophisticated neighborhood structures or repair mechanisms to navigate this challenging landscape.
        
    - **Instances `pr11`–`pr20`:** This group features **wider and less restrictive time windows**. With more temporal slack, finding a feasible solution is significantly easier. The challenge shifts from feasibility to pure optimization: finding the lowest-cost set of routes among a much larger set of feasible options.
        
- **Vehicle Availability (Resource Constraints):** The number of available vehicles is another critical parameter that is varied to create different levels of pressure. For certain instances, particularly `pr07` through `pr10` in the first group, the number of vehicles provided is assumed to be the minimum required to serve all customers.41 This creates a problem that is not only temporally constrained but also capacity-constrained, forcing an algorithm to make extremely efficient use of its limited vehicle resources.
    
- **Problem Scale:** The instances also vary in size, testing an algorithm's scalability. For example, by inspecting the instance files, one can determine that `pr01` involves 48 customers and 4 depots, while `pr11` is much larger, with 200 customers and 2 depots. This variation in the number of customers and depots ensures that algorithms are tested on both small and medium-large scale multi-depot problems.
    

This multi-dimensional design makes the `pr` set a formidable test of an algorithm's overall robustness. It creates a gradient of difficulty that moves from problems where the primary challenge is cost optimization (`pr11-pr20`) to problems where the primary challenge is satisfying a nexus of tight temporal and resource constraints (`pr01-pr10`). An algorithm that can perform well across this entire spectrum is likely to be robust and well-suited for complex, real-world applications where satisfying all operational constraints is often a more pressing concern than achieving the absolute theoretical minimum cost.

## Routing for Profit: An Analysis of Orienteering Problem (OP) Benchmarks

### The Orienteering Problem: Selecting and Routing

The Orienteering Problem (OP) and its multi-vehicle extension, the Team Orienteering Problem (TOP), represent a fundamental shift in the VRP paradigm from cost minimization to profit maximization.3 The problem is inspired by the sport of orienteering, where a competitor must visit a subset of checkpoints to maximize their score within a given time limit.44

Formally, the OP provides a set of locations, each with an associated score (or profit). The goal is to determine a single path that starts and ends at specified points, visits a subset of the locations, and maximizes the sum of the collected scores, all without exceeding a maximum time budget, `Tmax`.43 The TOP extends this to a fleet of vehicles, where the total score collected by the entire team is maximized, with the constraint that each location can be visited at most once by the entire team.45 This structure makes the OP a hybrid of two classic NP-hard problems: the Knapsack Problem (which locations to select to maximize value within a budget) and the Traveling Salesman Problem (what is the most efficient route between the selected locations).43

### Analysis of Foundational OP/TOP Benchmark Sets

Several benchmark sets have become standard for evaluating OP and TOP algorithms. The differences between them lie in their scale and, most importantly, how they vary the `Tmax` constraint to create different levels of difficulty.

- **Tsiligirides (1984):** These are among the earliest and smallest benchmark sets for the OP.47 They consist of instances with 21, 32, and 33 nodes and are primarily used to test the fundamental correctness and performance of new algorithmic ideas on manageable problems.48 The main parameter that varies within these sets is the
    
    `Tmax` budget.
    
- **Chao, Golden, and Wasil (1996):** This collection is one of the most extensive and widely cited for both OP and TOP.45 The instances within this collection are differentiated by several key parameters:
    
    - **Number of Nodes:** The sets include problems with varying numbers of locations, such as 21, 32, 64, 66, 100, and 102 nodes, allowing for scalability tests.49
        
    - **Number of Vehicles (m):** For the TOP instances, the fleet size is varied, typically between 2, 3, and 4 vehicles, which changes the nature of the customer partitioning problem.49
        
    - **Maximum Time Budget (Tmax):** This is the most crucial parameter for controlling difficulty. For a single set of node locations and scores, the authors generated multiple problem instances by systematically varying the `Tmax` value over a wide range.49
        
- **Fischetti et al. (1998):** To create larger and more complex OP instances, Fischetti and colleagues derived a benchmark set from existing, well-known VRP and TSP instances (e.g., from the TSPLIB library).47 This approach leverages the complex structures of these established problems to create challenging OP testbeds.
    

A key characteristic of OP/TOP benchmark design is the recognition that the problem's difficulty is a non-monotonic function of the `Tmax` constraint. This is a subtle but critical point. When `Tmax` is very large, the problem becomes easy: the optimal solution is simply to visit all profitable nodes, reducing the problem to a standard TSP (or m-TSP for the TOP). When `Tmax` is very small, the problem is also relatively easy: the solution is to visit the few highest-profit nodes that are closest to the depot.

The true challenge arises in the "critical region" where `Tmax` is at an intermediate value. In this region, the trade-offs are most complex. Should the route include a very high-profit node that is far away, consuming a large portion of the time budget? Or is it better to visit a cluster of lower-profit nodes that are close together? It is in this region, where the number of selected nodes is roughly half of the total available nodes, that the problem is hardest to solve.44 The Chao et al. benchmarks, by providing a wide range of

`Tmax` values for each node set, are explicitly designed to test an algorithm's performance across this entire spectrum of difficulty, and particularly its ability to navigate the complex decision-making required in the critical region.

## Synthesis and Recommendations for Benchmark Selection

### The Trajectory of VRP Benchmarks

The landscape of VRP benchmarks is not static; it is a dynamic reflection of 60 years of research in combinatorial optimization. The trajectory shows a clear and logical evolution from simple, abstract problems to large-scale, multi-attribute challenges that more closely mirror the complexities of real-world logistics. This evolution can be characterized by two key principles: **layered complexity** and **structured experimental design**.

The principle of layered complexity is evident in how new benchmark sets are often built upon the foundations of older ones. The Gehring & Homberger instances scale up the size of the Solomon problems, isolating the challenge of computational efficiency. The Li & Lim instances add pickup and delivery constraints to the Solomon framework, isolating the challenge of handling precedence and pairing. This methodological rigor allows researchers to attribute an algorithm's performance changes to specific problem features, enabling targeted algorithmic improvement.

The principle of structured experimental design is best exemplified by Solomon's original work. The 3x2 classification of instances (R/C/RC vs. Series 1/2) was a deliberate effort to create a diagnostic tool, not just a leaderboard. It allows for the systematic analysis of an algorithm's strengths and weaknesses in handling spatial versus temporal constraints. This structured approach has been so successful that it has been inherited by many subsequent benchmark sets. Together, these principles have created a rich and varied ecosystem of benchmarks that serve as the essential toolkit for any serious researcher in the field of vehicle routing.

### An Expert's Guide to Benchmark Selection

Choosing the right benchmark set is a critical first step in any research project on VRP algorithms. The selection should be guided by the specific research question being asked and the particular capabilities of the algorithm being tested. Based on the detailed analysis of the major benchmark families, the following recommendations can be made:

- **To Test Basic Routing and Scalability:**
    
    - **Target:** Algorithms for the classical Capacitated VRP (CVRP).
        
    - **Recommendation:** Begin with the foundational **CVRPLIB sets (A, B, E, F, M)** to establish baseline performance and test the handling of spatial structures (random vs. clustered). To test scalability and performance on problems where optimality is not guaranteed, progress to the larger instances from **Golden et al., Li et al., and Uchoa et al.**.7
        
- **To Diagnose Routing vs. Scheduling Performance:**
    
    - **Target:** Algorithms for the VRP with Time Windows (VRPTW).
        
    - **Recommendation:** Use the full set of **Solomon's 56 instances**. A detailed analysis of performance across the six classes (R1, C1, RC1, R2, C2, RC2) is essential. Comparing results between Series 1 and Series 2 instances will reveal the algorithm's effectiveness at scheduling versus packing, while comparing across R, C, and RC classes will diagnose its spatial reasoning capabilities.26
        
- **To Test Performance on Large-Scale Problems:**
    
    - **Target:** Heuristics designed for high efficiency and scalability on VRPTW.
        
    - **Recommendation:** Use the **Gehring & Homberger instances**, which scale from 200 to 1000 customers.14 These directly test the computational complexity and practical viability of an algorithm for industrial-sized problems.
        
- **To Test Handling of Precedence and Pairing Constraints:**
    
    - **Target:** Algorithms for the Pickup and Delivery Problem with Time Windows (PDPTW).
        
    - **Recommendation:** Use the **Li & Lim PDPTW instances**. To isolate the performance impact of the P&D logic, compare results on an `lr` instance with its corresponding `R` instance from Solomon, or an `lc` instance with its `C` counterpart. This directly measures the overhead and effectiveness of the algorithm's mechanisms for managing precedence and pairing.21
        
- **To Test Robustness Against Tight Constraints:**
    
    - **Target:** Advanced algorithms designed to navigate highly constrained, non-convex solution spaces.
        
    - **Recommendation:** Use the **Cordeau et al. `pr` instances**, specifically the first group (`pr01`–`pr10`).41 The combination of tight time windows and, in some cases, minimal vehicle availability creates an extreme test of an algorithm's ability to find feasible solutions.
        
- **To Test Profit-Maximization and Selection Strategies:**
    
    - **Target:** Algorithms for the Orienteering Problem (OP) or Team Orienteering Problem (TOP).
        
    - **Recommendation:** Use the **Chao, Golden, and Wasil TOP instances**. It is crucial to test across a wide range of `Tmax` values for a given node set. This ensures the algorithm is evaluated not only in easy regimes but also within the "critical region" of intermediate `Tmax` values, where the selection trade-offs are most difficult.44