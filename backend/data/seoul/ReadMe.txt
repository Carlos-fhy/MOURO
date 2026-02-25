New Realistic Sets of Benchmark Instances for Vehicle Routing Problem with Asymmetric Costs

Data abstract:
- Despite the importance, relatively little attention has been paid to vehicle routing problems with asymmetric costs (ACVRPs), or their benchmark instances. 
- Taking advantage of recent advances in map application programming interfaces (APIs) and shared spatial data, this paper proposes new realistic sets of ACVRP benchmark instances. 
- The spatial data of urban distribution centers, postal hubs, large shopping malls, residential complexes, restaurant businesses, and convenience stores are used. 
- To create distance and time matrices, the T map API, one of the most frequently used real time path analysis and distance measurement tools in South Korea, is used. 

54 data sets are provided
For each data set, 12 instances can be created (2 types of cost matrix, 2 types of vehicle capacities, 3 types of demand volumes)
This make the total of 648 ACVRP benchmark instances

- Each data set is named using the name city, depot, customers, and dimension (and distance range).
- In case of SLAS100, the city is Seoul, depot is logistics center (urban distribution center), customers are in residential facilities (apartments), and the dimension is small with the value of 100.

Each data set consists of the following:
- Coordinates.csv: x and y coordinates in WGS-84 format
- Cost_Distance.csv: road-distance matrix for each pair of nodes, from (row) and to (column)
- Cost_Time.csv: road-time matrix for each pair of nodes, from (row) and to (column)
- Vehicle_V1.csv: 1-ton truck's vehicle capacity in volume (cubic meters)
- Vehicle_V2.csv: 2.5-ton truck's vehicle capacity in volume (cubic meters)
- Volume_V1M5.csv: customer demand in volume (cubic meters), matched with Vehicle_V1.csv, case 1
- Volume_V1M10.csv: customer demand in volume (cubic meters), matched with Vehicle_V1.csv, case 2 
- Volume_V1M20.csv: customer demand in volume (cubic meters), matched with Vehicle_V1.csv, case 3
- Volume_V2M5.csv: customer demand in volume (cubic meters), matched with Vehicle_V2.csv, case 1
- Volume_V2M10.csv: customer demand in volume (cubic meters), matched with Vehicle_V2.csv, case 2
- Volume_V2M20.csv: customer demand in volume (cubic meters), matched with Vehicle_V2.csv, case 3
- Folder: Solutions

Each solution folder consists of the following:
- bestSolution.txt: best solution found in 10 replications
- solutionOFV.txt: OFV values for each replication
- solutionTime.txt: solution time for each replication (seconds)
* The solutions are provided using sweep and simulated annealing algorithms

Acknowledgments: 
Special thanks goes to Representative Director of SL Solution, Hyojoon Cha, and Director of Research Institute at SL Solution, Jaeseok Song. SL Solution, in charge of maintenance for the T map API, provided real time road distance and road time information for the benchmarks.
