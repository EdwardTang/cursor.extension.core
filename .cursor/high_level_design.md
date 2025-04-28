# High Level Design

1. **Requirements**: Understand the system's functional/nonfunctional requirements and constraints.
    <!-- Executor, PLEASE MAKE SURE removing this comment before your start writing actual requreiment. Here is a example for requirment:
    a Ghost Kitchens order fulfillment system has the following requirements:
   - **Real-time processing needs**: Orders arrive at configurable rate (e.g., 2/sec), couriers arrive after random delay (e.g., 2-6 seconds)
   - **Storage constraints**: Three storage options per `docs/Challenge.md` –  
     *Cooler* (6 cold), *Heater* (6 hot) and the room‑temperature *Shelf* (12).  
     When the ideal Cooler/Heater is full, the order goes to the Shelf; no separate
     "Overflow" shelf exists in the spec.
   - **Order lifecycle**: Each order must be placed on appropriate shelf, possibly moved, and ultimately picked up or discarded
   - **Freshness tracking**: Each order starts with `shelfLife` seconds of freshness.  
     • While on its **ideal** Cooler/Heater, freshness counts down at normal speed.  
     • While on the room‑temperature Shelf (i.e. not at its ideal temp), it decays
       **twice as fast** (half‑life rule from the spec).  
     There is no additional decay tier for a non‑existent "overflow" shelf.
   - **Discard logic**  
   1. **Expiry** – Remove (discard) any order whose freshness value is ≤ 0.  
   2. **Shelf‑full case** – When placing a new order and the Shelf is full:  
      a. Try moving an existing **cold** or **hot** order on the Shelf to its
         Cooler / Heater if space exists.  
      b. If no move is possible, discard the Shelf order that currently has the
         **lowest freshness value** (ties → oldest `placedTime`).  
     This minimises waste by sacrificing the item least likely to be delivered
     successfully. -->

2. **System Design**: Outline the high-level  architecture for the system.
   
    <!-- Agent who are reading this comment, PLEASE MAKE SURE removing this comment before your start writing actual design. Here is a example for design:
    A Ghost Kitchens order fulfillment system has the following design:
   - **Event-Driven Architecture**: The core pattern matches Ghost Kitchens' real systems where order events flow independently
   - Outline the high-level architecture and core use case's data flow diagrams in `docs/design.md` using mermaid syntax. for example:
     - Architecture diagram:
      ```mermaid
      <!-- sample mermaid diagram --> 
   ```
     
     - Core Use Case Data flow diagrams:
     
     1. Order Placement Flow:
     ```mermaid
     <!-- sample mermaid diagram -->
     ```
     
     3. Order Expiration Flow:
     ```mermaid
     <!-- sample mermaid diagram -->
     ```
   - **Main Components**:
     - Order Producer: Injects orders at specified rate, triggers "Order Placed" events
     - Shelves & Kitchen State: In-memory state management with thread-safe operations
     - Courier Scheduler: Schedules courier "Pickup events" after random delays
     - Kitchen State Manager: Processes pickup requests, removes orders from shelves
     - Expiration Monitor: Background process checking for expired orders
   - **Data Flow**: Orders progress through states (received → placed → possibly moved → picked up or discarded)
   - **Concurrency Model**: Thread pool (e.g., `ScheduledExecutorService`) with non-blocking design to process orders independently -->
   
3. **API Design**: Based on the system design, define core API endpoints and their relationships. for example:
    <!-- Agent who are reading this comment, PLEASE MAKE SURE removing this comment before your start writing actual API design. Here is a example for API design:
   - **Order Placement**:
     ```bash
     POST /v1/orders
     ```
     - Parameters: Order details (id, name, temp, shelfLife)
     - Response: Order status with placement information
     - Used to introduce new orders into the system

   - **Order Pickup**:
     ```bash
     POST /v1/orders/{id}/pickup
     ```
     - Parameters: Order ID (path parameter)
     - Response: Pickup confirmation with order details and freshness value
     - Handles courier pickup operations

   - **Shelf Status**:
     ```bash
     GET /v1/shelves
     ```
     - Parameters: None
     - Response: Current status of all shelves with their orders
     - Provides visibility into kitchen state

   - **Order Status**:
     ```bash
     GET /v1/orders/{id}
     ```
     - Parameters: Order ID (path parameter)
     - Response: Detailed order information including current status and history
     - For tracking individual orders

   - **Kitchen Action Ledger**:
     ```bash
     GET /v1/actions
     ```
     - Parameters: Optional filters (orderId, action type, time range)
     - Response: Chronological list of kitchen actions (place, move, pickup, discard)
     - Captures the complete history of order management

   - **Challenge Server Interaction**: Based on the system design, define interaction points with the external Challenge Server.
     - **Fetch Orders**: `GET https://api.ghostkitchens.com/interview/challenge/new` (Handled by harness/client)
       - Uses `auth` token, receives `x-test-id` and order list JSON.
     - **Submit Actions**: `POST https://api.ghostkitchens.com/interview/challenge/solve` (Handled by harness/client)
       - Uses `auth` token and `x-test-id` header.
       - Sends JSON body containing simulation options (rate, pickup times) and the list of timestamped actions (place, move, pickup, discard).
       - Receives pass/fail result string.
     - **Internal Simulation Logic**: The core system (Kitchen, Shelves, Order) manages the state and generates the action list internally, driven by scheduled events, without exposing its own HTTP API.-->

4. **Data Models**: Based on the API Design, define core data structures and their relationships. for example:
    <!-- Executor, PLEASE MAKE SURE removing this comment before your start writing actual data models. Here is a example for data models:
   - **Order Class**: Contains order details and methods to track shelf placement and value
     ```java
     public class Order {
         private final String id;
         private final String name;
         private final Temperature temp;  // enum for HOT/COLD/ROOM_TEMP
         private final int shelfLife;     // shelf life in seconds
         private final double decayRate = 1.0; // decay rate assumed 1.0 if not provided? Challenge.md doesn't specify it.
         private volatile Shelf currentShelf;
         private final long createdOrMovedTimeNanos; // Use nanoTime for monotonic time

         // Enum for Temperature and ShelfType should be defined elsewhere
         // e.g., public enum Temperature { HOT, COLD, ROOM_TEMP }
         // e.g., public enum ShelfType { HOT, COLD, ROOM_TEMP }

         // Constructor
         public Order(String id, String name, Temperature temp, int shelfLife) {
             this.id = id;
             this.name = name;
             this.temp = temp;
             this.shelfLife = shelfLife;
             // Initialize placement time when actually placed
             this.createdOrMovedTimeNanos = System.nanoTime();
         }

         // Calculate current value (freshness) based on time since placement/move
         public synchronized double getCurrentValue() {
             // Use nanoTime for monotonic age calculation
             long ageNanos = System.nanoTime() - createdOrMovedTimeNanos;
             long ageSeconds = TimeUnit.NANOSECONDS.toSeconds(ageNanos);
             
             // Shelf decay modifier based on the spec (double decay if not on ideal temp)
             Shelf current = this.currentShelf; // Volatile read
             boolean onIdealShelf = (current != null) && 
                                  ((temp == Temperature.HOT  && current.getType() == ShelfType.HOT ) ||
                                   (temp == Temperature.COLD && current.getType() == ShelfType.COLD) ||
                                   (temp == Temperature.ROOM_TEMP && current.getType() == ShelfType.ROOM_TEMP)); // ROOM_TEMP ideal shelf is ROOM_TEMP
             double shelfDecayMod = onIdealShelf ? 1.0 : 2.0;  // off-temperature halves freshness time

             double value = (double)(shelfLife - decayRate * ageSeconds * shelfDecayMod) / shelfLife;
             return Math.max(value, 0.0);
         }

         // Thread-safe shelf placement method (updates state and timer)
         public synchronized void placeOnShelf(Shelf shelf) {
             this.currentShelf = shelf;
             this.createdOrMovedTimeNanos = System.nanoTime(); // Reset timer on placement/move
         }

         // Getters
         public String getId() { return id; }
         public Temperature getTemp() { return temp; }
         public Shelf getCurrentShelf() { return currentShelf; }
         public long getCreatedOrMovedTimeNanos() { return createdOrMovedTimeNanos; }
     }
     ```
   
   - **Shelf Class**: Represents each shelf type with thread-safe operations
     ```java
     public class Shelf {
         private final ShelfType type;
         private final int capacity;
         private final List<Order> orders = new ArrayList<>();
         
         public Shelf(ShelfType type, int capacity) {
             this.type = type;
             this.capacity = capacity;
         }
         
         public ShelfType getType() { return type; }
         
         // Thread-safe shelf operations
         public synchronized boolean isFull() {
             return orders.size() >= capacity;
         }
         
         public synchronized boolean isEmpty() {
             return orders.isEmpty();
         }
         
         public synchronized void addOrder(Order order) {
             if (orders.size() >= capacity) throw new IllegalStateException("Shelf full");
             orders.add(order);
             order.placeOnShelf(this); // Use dedicated method to set shelf and time
         }
         
         public synchronized Order removeOrder(Order order) {
             if (orders.remove(order)) {
                 return order;
             }
             return null;
         }
         
         public synchronized Order removeAny() {
             // Changed from random to lowest value discard strategy
             return removeLowestValueOrder();
         }
         
         // Added method for explicit lowest value removal
         private synchronized Order removeLowestValueOrder() {
             if (orders.isEmpty()) return null;
             
             Order lowestValueOrder = null;
             double lowestValue = Double.MAX_VALUE;
             
             for (Order order : orders) {
                 double value = order.getCurrentValue();
                 if (value < lowestValue) {
                     lowestValue = value;
                     lowestValueOrder = order;
                 }
             }
             
             if (lowestValueOrder != null) {
                 orders.remove(lowestValueOrder);
             }
             return lowestValueOrder;
         }
         
         public synchronized List<Order> getOrdersSnapshot() {
             return new ArrayList<>(orders);  // copy for safe iteration
         }
     }
     ```
   
   - **Kitchen Coordinator**: Central component managing all shelves and order placement logic
     ```java
     public class Kitchen {
         private final Shelf hotShelf;
         private final Shelf coldShelf;
         private final Shelf roomTempShelf; 
         private final ConcurrentHashMap<String, Order> ordersById = new ConcurrentHashMap<>();

         // Capacities defined by Challenge.md
         public Kitchen() {
             this.hotShelf = new Shelf(ShelfType.HOT, 6);
             this.coldShelf = new Shelf(ShelfType.COLD, 6);
             this.roomTempShelf = new Shelf(ShelfType.ROOM_TEMP, 12);
         }
         
         // Helper to get the primary shelf based on temperature
         private Shelf getPrimaryShelfForTemp(Temperature temp) {
             switch (temp) {
                 case HOT: return hotShelf;
                 case COLD: return coldShelf;
                 case ROOM_TEMP: return roomTempShelf; 
                 default: throw new IllegalArgumentException("Unsupported temperature: " + temp);
             }
         }

         // Helper to get the shelf object from its type
         private Shelf getShelfByType(ShelfType type) {
             switch (type) {
                 case HOT: return hotShelf;
                 case COLD: return coldShelf;
                 case ROOM_TEMP: return roomTempShelf;
                 default: return null; // Should not happen
             }
         }
         
         // Core methods: place orders, pickup orders, and remove expired orders
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
             synchronized(roomTempShelf) {
                 if (!roomTempShelf.isFull()) {
                     roomTempShelf.addOrder(order);
                     logAction("PLACED", order, roomTempShelf.getType());
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
             } else {
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
         
         public void removeExpiredOrders() {
             // Only need to check Hot, Cold, and Room Temp shelves
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
     }
     ``` -->

5. **Tech Stack at High Level: Components Deep Dive**: 
    <!-- Executor, PLEASE MAKE SURE removing this comment before writing actual components deep dive. Here is a example for components deep dive:
   - **System Architecture (Challenge Implementation)**:
     - Event-driven Architecture: Optimized for real-time order processing, leveraging a message bus core (e.g., Kafka via `quarkus-smallrye-reactive-messaging-kafka`).
     - Single-Process Simulation: Command-line harness driving in-memory state changes.
     - Concurrency Model: Core Java Concurrency (`ExecutorService`, `ScheduledExecutorService`, `synchronized`, `ConcurrentHashMap`) is used for the simulation.
     - Data Structures: Thread-safe collections (`ConcurrentHashMap`) and careful synchronization (`synchronized` blocks, considering lock ordering like HOT < COLD < ROOM_TEMP) are employed.

6. ** Deployment and Monitoring at High Level**: Based on `.cursor/high_level_design.md` and above requirements, identify and employ necessary deployment and monitoring strategies.
    <!-- Executor, PLEASE MAKE SURE removing this comment before writing actual deployment and monitoring. Here is a example for deployment and monitoring:
    - **Cloud, Hybrid, On-Premise, Self-Hosted Deployment**
        - **Cloud Providers**:
            - **AWS**:
            - **Azure**:
            - **GCP**:
    - **Deployment Strategies**:
        - **Blue/Green Deployment**
        - **Canary Deployment**
        - **Rolling Deployment**
    - **Monitoring Strategies**:
        - **Health Checks**: Endpoint-based monitoring to verify service availability and basic functionality
        - **Metrics Collection**: Gathering quantitative data on system performance (response times, throughput, error rates)
        - **Distributed Tracing**: Following requests across service boundaries to identify bottlenecks
        - **Log Aggregation**: Centralized collection and analysis of application logs
        - **Synthetic Monitoring**: Simulating user interactions to detect issues before real users encounter them
        - **Real User Monitoring (RUM)**: Capturing actual user experience metrics from production traffic
        - **Infrastructure Monitoring**: Tracking host-level metrics (CPU, memory, disk, network)
        - **Dependency Monitoring**: Observing the health of external services and databases
        - **SLO/SLA Monitoring**: Tracking compliance with service level objectives
        - **Anomaly Detection**: Using ML/statistical methods to identify unusual patterns
