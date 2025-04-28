
1. **Requirements**: Based on `.cursor/high_level_design.md`, identify necessary supporting requirements at low-level implementation.
   <!-- Executor, PLEASE MAKE SURE removing this comment before writing actual requirements. Here is a example for low level requirements:
   - **Concurrency and Synchronization**:
     - Define thread safety requirements for shared resources
     - Specify locking strategies (optimistic vs. pessimistic)
     - Identify critical sections requiring atomic operations
   - **Fault Tolerance**:
     - Define error handling and recovery mechanisms
     - Specify timeout values and retry policies
     - Implement circuit breakers for external dependencies
   - **State Management**:
     - Define state transitions and validation rules
     - Specify persistence requirements (durability guarantees)
     - Implement idempotency mechanisms for operations
   - **Communication Protocols**:
     - Define message formats and serialization standards
     - Specify request/response patterns and error codes
     - Implement backpressure mechanisms for overload protection
   - **Monitoring and Observability**:
     - Define key metrics to be collected
     - Specify logging requirements (levels, formats)
     - Implement health check endpoints

2. **Utilities**: Based on `.cursor/high_level_design.md` and above requirements, identify and implement necessary supporting functions.
    <!-- Agent who are reading this comment, PLEASE MAKE SURE removing this comment before your start writing actual utilities. Here is a example for utilities:
   - **Thread Management (Challenge Implementation)**:
     - `ExecutorService` / `ScheduledExecutorService` for scheduling tasks (order production, courier pickups, expiration checks). Use Virtual Threads factory if enabled.
     - Thread-safe collections (`ConcurrentHashMap`) for central order lookup.
   - **Time Handling**:
     - Functions to calculate order age and freshness value (consider `System.nanoTime()` for monotonic time).
     - Use `ScheduledExecutorService` for courier arrival and order expiration checks.
   - **Logging**:
     - Action logger for shelf operations (place, move, pickup, discard, expired) - use standard output.
     - Timestamping functions for event tracking.
     - Order state tracking (delivered vs. wasted counts) using `AtomicInteger`.
   -->

3. **Tech Stack at Low Level: Implementation Deep Dive**: Based on `.cursor/high_level_design.md` and above requirements, deep dive into engineering best practices (e.g.DDD, OOD, SOLID, or TDD, etc.), design patterns, technology stack (e.g. microservice framework, database, cache, message queue, etc.), programming language features, core algorithms, multithreading, concurrency, synchronization, fault tolerance, security, and compliance etc. 
    <!-- Executor, PLEASE MAKE SURE removing this comment beforewriting actual implementation Deep Dive. Here is a example for implementation Deep Dive:
   - **Shelf Selection Algorithm**: Implement the logic for placing orders on appropriate shelves
     ```java
     public void placeOrder(Order order) {
         ordersById.put(order.getId(), order);
         
         Shelf primaryShelf = getPrimaryShelfForTemp(order.getTemp());
         
         // Lock primary shelf first
         synchronized (primaryShelf) {
             if (!primaryShelf.isFull()) {
                 primaryShelf.addOrder(order);
                 logAction("PLACED", order, primaryShelf.getType());
                 return;
             }
         }
         
         // Cooler/Heater full or order is ROOM_TEMP -> place candidate on Shelf (roomTempShelf)
         // Ensure locking order: RoomTempShelf is likely last in order (e.g., HOT < COLD < ROOM_TEMP)
         if (primaryShelf != roomTempShelf) {
             synchronized (roomTempShelf) {
                 if (!roomTempShelf.isFull()) {
                     roomTempShelf.addOrder(order);
                     logAction("PLACED", order, ShelfType.ROOM_TEMP);
                     return;
                 }
             
                 // Shelf full – try to move a cold/hot Shelf order back to its Cooler/Heater
                 // According to the spec, we need to check if we can move *any* eligible order
                 // from the roomTempShelf to its ideal Cooler/Heater shelf if space exists there.
                 // This must happen BEFORE discarding from roomTempShelf.
                 boolean moved = tryMoveShelfOrderToIdeal(); // This helper needs locks

             // If a move occurred, roomTempShelf might have space now. If not, or if still full, discard.
             if (!roomTempShelf.isFull()) { // Re-check after potential move
                 roomTempShelf.addOrder(order);
                 logAction("PLACED", order, ShelfType.ROOM_TEMP);
                 return;
             }
         
                 // If still full (no move possible or still not enough space), discard the lowest value order from roomTempShelf
                 Order orderToDiscard = roomTempShelf.removeLowestValueOrder(); 
                 if (orderToDiscard != null) {
                     ordersById.remove(orderToDiscard.getId());
                     logAction("DISCARD", orderToDiscard, ShelfType.ROOM_TEMP); // Use DISCARD action name
                     
                     // Now place the new order on the roomTempShelf (space was just made)
                     roomTempShelf.addOrder(order);
                     logAction("PLACED", order, ShelfType.ROOM_TEMP);
                 } else {
                     // Should not happen if shelf was full, but handle defensively
                     logAction("ERROR", order, ShelfType.ROOM_TEMP); // Log error - couldn't place or discard
                     System.err.println(formatTimestamp() + " CRITICAL_ERROR: Could not place order " + order.getId() + " on full room temp shelf and could not discard.");
                     // Potentially remove the order we failed to place?
                     ordersById.remove(order.getId()); 
                 }
             }
         }
     }
     
     // Helper method to try moving ONE order from roomTempShelf to its ideal shelf
     // Returns true if a move was successful, false otherwise.
     private boolean tryMoveShelfOrderToIdeal() {
         // Iterate over a snapshot to avoid ConcurrentModificationException
         List<Order> roomTempOrders = roomTempShelf.getOrdersSnapshot(); // Get copy for iteration

         for (Order orderToMove : roomTempOrders) {
             // Only consider moving HOT or COLD orders off the room temp shelf
             if (orderToMove.getTemp() == Temperature.HOT || orderToMove.getTemp() == Temperature.COLD) {
                 Shelf targetShelf = getPrimaryShelfForTemp(orderToMove.getTemp()); // Hot or Cold shelf

                 // Acquire locks in fixed order (e.g., by ShelfType ordinal) to prevent deadlock
                 // Assuming order HOT < COLD < ROOM_TEMP
                 Shelf firstLock = targetShelf.getType().ordinal() < roomTempShelf.getType().ordinal() ? targetShelf : roomTempShelf;
                 Shelf secondLock = firstLock == targetShelf ? roomTempShelf : targetShelf;

                 synchronized (firstLock) {
                     synchronized (secondLock) {
                         // Double-check conditions after acquiring locks
                         if (!targetShelf.isFull()) {
                             // Ensure the order is still on the roomTempShelf (could have been picked up/expired)
                             Order currentOrder = ordersById.get(orderToMove.getId()); // Check master map
                             if (currentOrder != null && currentOrder.getCurrentShelf() == roomTempShelf) {
                                 // Perform the move
                                 if (roomTempShelf.removeOrder(currentOrder) != null) { // Ensure removal success
                                     targetShelf.addOrder(currentOrder); // Add to target
                                     logAction("MOVE", currentOrder, targetShelf.getType()); // Use MOVE action name
                                     return true; // Moved one order, that's enough for now
                                 } else {
                                     // Log if removal failed unexpectedly (e.g., race condition)
                                     System.err.println(formatTimestamp() + " MOVE_ERROR: Failed to remove order " + currentOrder.getId() + " from room temp shelf during move attempt.");
                                 }
                             }
                         }
                     }
                 }
             }
         }
         return false; // No suitable order found or no space on target shelves
     }
     
     // This specific discard selection logic is now primarily handled within Kitchen.placeOrder
     // when the roomTempShelf is full and no move is possible.
     // removeLowestValueOrder() in Shelf class provides the mechanism.
     private Order selectOrderForDiscard() {
         // This method is likely no longer needed here as the logic is in placeOrder
         return null;
     }
     ```
   
   - **Order Pickup Implementation**: Handle courier arrival and order pickup
     ```java
     public void pickupOrder(String orderId) {
         Order order = ordersById.get(orderId);
         if (order == null) {
             // Order not found (possibly already discarded)
             System.out.println(formatTimestamp() + " COURIER_MISS: Order " + orderId + " not found (possibly already discarded)");
             return;
         }
         
         Shelf shelf = order.getCurrentShelf();
         synchronized(shelf) {
             if (shelf.removeOrder(order) != null) {
                 // Order successfully removed
                 double value = order.getCurrentValue();
                 ordersById.remove(orderId);
                 logAction("PICKED_UP", order, shelf.getType());
                 
                 // Track statistics
                 deliveredCount.incrementAndGet();
                 
                 // If value <= 0, order was technically "waste" at pickup time
                 if (value <= 0) {
                     System.out.println(formatTimestamp() + " WARNING: Order " + orderId + 
                                        " was picked up with zero value (expired)");
                 }
             } else {
                 // Order not found on shelf (race condition, picked up by another thread)
                 System.out.println(formatTimestamp() + " COURIER_MISS: Order " + orderId + 
                                    " not found on expected shelf (likely discarded or race condition)");
             }
         }
     }
     ```
   
   - **Order Expiration Monitor**: Periodically scan shelves for expired orders
     ```java
     public void removeExpiredOrders() {
         Shelf[] allShelves = new Shelf[]{hotShelf, coldShelf, roomTempShelf};
         
         for (Shelf shelf : allShelves) {
             synchronized(shelf) {
                 List<Order> orders = shelf.getOrdersSnapshot();
                 for (Order order : orders) {
                     if (order.getCurrentValue() <= 0) {
                         // Order has expired, remove it
                         if (shelf.removeOrder(order) != null) { // Check if remove succeeded (wasn't picked up concurrently)
                             ordersById.remove(order.getId());
                             logAction("DISCARD", order, shelf.getType()); // Log as DISCARD (reason: expired)
                             // Track statistics
                             wastedCount.incrementAndGet();
                         }
                     }
                 }
             }
         }
     }
     ```
   
   - **Order Producer and Courier Scheduling**:
     ```java
     public void startSimulation(List<Order> orders, double orderRate, int minPickupDelay, int maxPickupDelay) {
         // Calculate interval between orders in milliseconds
         long orderIntervalMs = (long)(1000 / orderRate);
         
         // Create thread pools - consider using Virtual Threads if JDK 21+
         // ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(4); // Platform threads
         ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(4, Thread.ofVirtual().factory()); // Virtual threads (JDK 21+)
         
         ThreadLocalRandom random = ThreadLocalRandom.current();
         
         // Process each order
         AtomicInteger index = new AtomicInteger(0);
         
         // Schedule order production at fixed rate
         scheduler.scheduleAtFixedRate(() -> {
             int i = index.getAndIncrement();
             if (i >= orders.size()) {
                 // All orders processed, check if we can shut down
                 if (ordersById.isEmpty()) {
                     scheduler.shutdown();
                     printSummary();
                 }
                 return;
             }
             
             Order order = orders.get(i);
             
             // Place order in kitchen
             placeOrder(order);
             
             // Schedule courier pickup with random delay
             int pickupDelay = random.nextInt(minPickupDelay, maxPickupDelay + 1);
             scheduler.schedule(() -> {
                 pickupOrder(order.getId());
             }, pickupDelay, TimeUnit.SECONDS);
             
         }, 0, orderIntervalMs, TimeUnit.MILLISECONDS);
         
         // Schedule expired order checker (every 1 second)
         scheduler.scheduleAtFixedRate(this::removeExpiredOrders, 1, 1, TimeUnit.SECONDS);
     }
     ```
   
   - **Logging and Action Tracking**:
     ```java
     private final AtomicInteger deliveredCount = new AtomicInteger(0);
     private final AtomicInteger wastedCount = new AtomicInteger(0);
     private final long startTime = System.currentTimeMillis();
     
     private String formatTimestamp() {
         long elapsed = System.currentTimeMillis() - startTime;
         return String.format("[+%.3fs]", elapsed / 1000.0);
     }
     
     private void logAction(String action, Order order, ShelfType shelfType) {
         // Value calculation might need care if called outside locks or if state changes
         double value = order.getCurrentValue(); 
         String message = String.format("%s %-9s Order %s (%s, temp=%s) %s %s Shelf (Value: %.2f)",
             formatTimestamp(),
             action,
             order.getId(),
             order.getName(), // Assuming Order has getName()
             order.getTemp(),
             action.equals("PLACED") || action.equals("MOVE") ? "on" : "from",
             shelfType,
             value
         );
         System.out.println(message);
     }
     
     private void printSummary() {
         int delivered = deliveredCount.get();
         int wasted = wastedCount.get();
         // Assuming ordersReceived is tracked elsewhere or calculated
         int totalAttempted = delivered + wasted + ordersById.size(); // Approximate total if not tracked explicitly
         double successRate = (totalAttempted > 0) ? (delivered * 100.0) / totalAttempted : 0.0;

         System.out.println("\n=== SIMULATION SUMMARY ===");
         System.out.println("Total orders processed (attempted/completed): " + totalAttempted);
         System.out.println("Successfully delivered: " + delivered);
         System.out.println("Wasted/discarded (including expired): " + wasted);
         System.out.println("Remaining on shelves: " + ordersById.size());
         System.out.println("Delivery success rate (delivered / total attempted): " + String.format("%.1f%%", successRate));
         System.out.println("==========================\n");
     }
     ```
   
   - **Main Application Entry Point**:
     ```java
     public static void main(String[] args) throws Exception {
         // Parse command line arguments for configuration
         double orderRate = 2.0; // default: 2 orders/second
         int minPickupDelay = 4;  // default: 4 seconds
         int maxPickupDelay = 8;  // default: 8 seconds
         String ordersFile = "orders.json";
         String authToken = null; // Required
         
         // Override defaults with command line args if provided
         // Use Picocli or similar for robust parsing
         // Example: authToken = getArg("--auth", args);
         // Example: orderRate = Double.parseDouble(getArg("--rate", args, "2.0"));
         
         // Load orders from JSON file
         // OR: Fetch orders from Challenge Server using authToken and client
         ChallengeClient client = new ChallengeClient(authToken);
         TestProblem problem = client.fetchNewProblem();
         List<Order> orders = problem.getOrders();
         String testId = problem.getTestId();
         
         // Create kitchen - adjust capacities based on requirements or config
         Kitchen kitchen = new Kitchen(); // Uses fixed capacities from Challenge.md
         
         // Start simulation
         SimulationService simService = new SimulationService(kitchen, client, testId);
         simService.runSimulation(orders, orderRate, minPickupDelay, maxPickupDelay);
         
         // Wait for simulation to complete
         // SimulationService.runSimulation should block or provide a way to wait
         // e.g., simService.awaitCompletion();
         
         // Submit results
         simService.submitResults();
     }
     ``` -->

4. **Optimization and Performance Tuning at Low Level**: Tune implementation for performance and better business metrics.
    <!-- Executor, PLEASE MAKE SURE removing this comment before your start writing actual optimization. Here is a example for optimization:
   - **Intelligent Discard Strategy**: Instead of random discard (or simple lowest value), consider more sophisticated strategies like Least Recently Used (LRU) or combination factors if needed. The current "lowest value" strategy is a good starting point.
   - **Lock Granularity**: Evaluate if `synchronized` blocks become bottlenecks. Consider finer-grained locks (e.g., `ReentrantLock`) or lock-free structures if profiling shows contention. See note in Tech Stack section.
   - **Thread Pool Sizing**: Adjust thread pool sizes (especially if using platform threads) based on expected load and available cores. Virtual threads largely mitigate this concern.
   - **Value Calculation Optimization**: Cache or reduce frequency of value recalculation to minimize CPU impact
   - **Shelf Management**: Consider keeping temperature-sensitive orders on their ideal shelves when possible

5. **Quality Assurance**: Ensure the system handles edge cases and failure scenarios.
    <!-- Agent who are reading this comment, PLEASE MAKE SURE removing this comment before your start writing actual quality assurance. Here is a example for quality assurance:
   - **Functional Tests**:
     - Verify shelf operations (add, remove, move between shelves) for all types (Hot, Cold, Room Temp).
   - **Concurrency Tests**:
     - High-load scenarios (many orders arriving simultaneously)
     - Edge cases (very short shelf life orders, all shelves full)
     - Race conditions (order expiring exactly at pickup time)
   - **Fault Tolerance**:
     - Exception handling in all thread operations
     - Graceful shutdown ensuring all orders are accounted for
     - Verification that orders are either delivered or explicitly discarded (check `printSummary` logic).
   - **Validation**:
     - Confirm total orders = delivered + wasted
     - Verify action ledger shows complete history for each order

6. **Deployment, Experimentation and Monitoring**: Based on `.cursor/high_level_design.md` and above requirements, identify and employ necessary deployment and monitoring tools.
    <!-- Executor, PLEASE MAKE SURE removing this comment before your start writing actual deployment and monitoring. Here is a example for deployment and monitoring:
   - **Containerization**: Use Docker for containerization
   - **Orchestration**: Kubernetes for orchestration
   - **Monitoring**: Prometheus and Grafana for monitoring
   - **Logging**: Log4j for logging
   - **Alerting**: Alertmanager for alerting
   - **Security**: Spring Security for security
   - **Experimentation**: A/B testing with Statsig 