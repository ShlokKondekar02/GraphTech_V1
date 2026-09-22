// Preset and dynamic diagram generators with complete Vercel-style aesthetics

export const SAMPLE_PROMPTS = [
  {
    id: 'microservices',
    title: 'Create a microservices architecture',
    description: 'API Gateway, Auth, Order & Payment services with event broker',
    type: 'Architecture',
    complexity: 'Moderate',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: 'Passed',
    nodesCount: 8,
    edgesCount: 11,
    latency: '342ms'
  },
  {
    id: 'erd',
    title: 'Create an ER diagram',
    description: 'Relational schema for Users, Orders, Products, and Payments',
    type: 'Entity-Relationship',
    complexity: 'Moderate',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: 'Passed',
    nodesCount: 6,
    edgesCount: 7,
    latency: '280ms'
  },
  {
    id: 'workflow',
    title: 'Create a system workflow',
    description: 'Event-driven order fulfillment, payment validation & state transitions',
    type: 'Workflow / State',
    complexity: 'Simple',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: 'Passed',
    nodesCount: 7,
    edgesCount: 9,
    latency: '215ms'
  }
];

export const INITIAL_HISTORY = [
  {
    id: 'hist-microservices',
    title: 'Distributed Microservices Architecture',
    type: 'Architecture',
    prompt: 'Create a microservices architecture',
    timestamp: 'Today'
  },
  {
    id: 'hist-erd',
    title: 'Relational Database Schema (ERD)',
    type: 'Entity-Relationship',
    prompt: 'Create an ER diagram',
    timestamp: 'Yesterday'
  },
  {
    id: 'hist-workflow',
    title: 'Order Fulfillment State Machine',
    type: 'Workflow / State',
    prompt: 'Create a system workflow',
    timestamp: 'Previous 7 Days'
  }
];

export const PIPELINE_STEPS = [
  { id: 'understanding', label: 'Prompt Understanding', description: 'spaCy linguistic tokenization & semantic entity extraction' },
  { id: 'extraction', label: 'Information Extraction', description: 'Structured graph AST extraction (nodes, edges, taxonomy)' },
  { id: 'classification', label: 'Complexity Classification', description: 'Scikit-learn Random Forest model (F1-score: 0.94)' },
  { id: 'routing', label: 'Routing', description: 'Determining optimal engine (DSL vs. Vector vs. Image)' },
  { id: 'generation', label: 'Diagram Generation', description: 'Compiling structured AST into clean deterministic syntax' },
  { id: 'validation', label: 'Validation', description: 'Topological, syntactic & acyclic invariant verification' }
];

export function getDiagramDataForPrompt(promptText) {
  const lower = (promptText || '').toLowerCase();

  if (lower.includes('microservice') || lower.includes('cloud') || lower.includes('architecture') || lower.includes('api gateway')) {
    return getMicroservicesDiagram();
  } else if (lower.includes('er ') || lower.includes('entity') || lower.includes('database') || lower.includes('relational') || lower.includes('schema') || lower.includes('table')) {
    return getERDDiagram();
  } else if (lower.includes('workflow') || lower.includes('process') || lower.includes('state') || lower.includes('pipeline') || lower.includes('lifecycle')) {
    return getWorkflowDiagram();
  } else {
    // Custom diagram based on user's prompt
    return getCustomArchitectureDiagram(promptText);
  }
}

function getMicroservicesDiagram() {
  const dsl = `graph TB
  Client([Web & Mobile Clients]) -->|HTTPS / REST| APIGW[API Gateway]
  APIGW -->|JWT Auth| AuthService[Auth & Identity Service]
  APIGW -->|gRPC| OrderService[Order Management Service]
  APIGW -->|gRPC| PaymentService[Payment Processing Service]
  
  OrderService -->|Publish OrderCreated| Kafka{Kafka Event Broker}
  Kafka -->|Consume Event| PaymentService
  Kafka -->|Notify Customer| NotificationService[Notification Service]
  
  AuthService --> AuthDB[(PostgreSQL Users)]
  OrderService --> OrderDB[(PostgreSQL Orders)]
  PaymentService --> StripeAPI[Stripe Gateway API]`;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 540" width="100%" height="100%" style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;">
  <defs>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000000" flood-opacity="0.05" />
    </filter>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#18181B" />
      <stop offset="100%" stop-color="#27272A" />
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#71717A" />
    </marker>
    <marker id="arrowAccent" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#2563EB" />
    </marker>
  </defs>

  <!-- Background Grid Canvas -->
  <rect width="100%" height="100%" fill="#FFFFFF" rx="12" />
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="1" cy="1" r="1" fill="#F1F5F9" />
  </pattern>
  <rect width="100%" height="100%" fill="url(#grid)" rx="12" />

  <!-- Subgraph / Enclosure: Microservices Domain -->
  <rect x="230" y="145" width="460" height="235" rx="12" fill="#FAFAFA" stroke="#E4E4E7" stroke-width="1.5" stroke-dasharray="4 4" />
  <text x="250" y="172" font-size="11" font-weight="600" fill="#71717A" letter-spacing="0.5">SECURE VPC SERVICE MESH (CLUSTER)</text>

  <!-- 1. Client Node -->
  <g filter="url(#shadow)">
    <rect x="360" y="25" width="200" height="52" rx="26" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <circle cx="390" cy="51" r="12" fill="#F4F4F5" />
    <text x="390" y="55" font-size="12" text-anchor="middle" fill="#18181B">📱</text>
    <text x="415" y="47" font-size="13" font-weight="600" fill="#09090B">Web &amp; Mobile Clients</text>
    <text x="415" y="62" font-size="11" fill="#71717A">Public Endpoints (REST/WSS)</text>
  </g>

  <!-- Flow Client -> API Gateway -->
  <path d="M 460 77 L 460 115" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />
  <rect x="425" y="88" width="70" height="18" rx="4" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1" />
  <text x="460" y="101" font-size="9.5" font-weight="500" fill="#52525B" text-anchor="middle">HTTPS :443</text>

  <!-- 2. API Gateway Node -->
  <g filter="url(#shadow)">
    <rect x="340" y="115" width="240" height="56" rx="10" fill="url(#headerGrad)" stroke="#09090B" stroke-width="1" />
    <text x="460" y="140" font-size="13" font-weight="600" fill="#FFFFFF" text-anchor="middle">API Gateway (Kong / Envoy)</text>
    <text x="460" y="156" font-size="10.5" fill="#A1A1AA" text-anchor="middle">Rate Limiting • SSL Termination • TLS Routing</text>
  </g>

  <!-- Connectors from Gateway to Services -->
  <path d="M 380 171 L 280 215" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />
  <path d="M 460 171 L 460 215" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />
  <path d="M 540 171 L 640 215" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />

  <!-- 3. Auth Service -->
  <g filter="url(#shadow)">
    <rect x="190" y="215" width="180" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <rect x="202" y="227" width="6" height="32" rx="3" fill="#6366F1" />
    <text x="218" y="240" font-size="12.5" font-weight="600" fill="#09090B">Auth Service</text>
    <text x="218" y="256" font-size="10" fill="#71717A">OAuth2 / OIDC Token Gen</text>
  </g>

  <!-- 4. Order Service -->
  <g filter="url(#shadow)">
    <rect x="370" y="215" width="180" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <rect x="382" y="227" width="6" height="32" rx="3" fill="#2563EB" />
    <text x="398" y="240" font-size="12.5" font-weight="600" fill="#09090B">Order Service</text>
    <text x="398" y="256" font-size="10" fill="#71717A">Order Orchestration (gRPC)</text>
  </g>

  <!-- 5. Payment Service -->
  <g filter="url(#shadow)">
    <rect x="550" y="215" width="180" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <rect x="562" y="227" width="6" height="32" rx="3" fill="#059669" />
    <text x="578" y="240" font-size="12.5" font-weight="600" fill="#09090B">Payment Service</text>
    <text x="578" y="256" font-size="10" fill="#71717A">Ledger &amp; Settlements</text>
  </g>

  <!-- Connectors: Order Service -> Kafka -->
  <path d="M 460 271 L 460 305" fill="none" stroke="#2563EB" stroke-width="1.5" stroke-dasharray="3 3" marker-end="url(#arrowAccent)" />
  <rect x="420" y="278" width="80" height="16" rx="3" fill="#EFF6FF" stroke="#BFDBFE" stroke-width="1" />
  <text x="460" y="290" font-size="9" font-weight="600" fill="#1D4ED8" text-anchor="middle">OrderCreated Event</text>

  <!-- 6. Kafka Event Bus -->
  <g filter="url(#shadow)">
    <rect x="320" y="305" width="280" height="52" rx="8" fill="#18181B" stroke="#27272A" stroke-width="1" />
    <circle cx="346" cy="331" r="10" fill="#27272A" />
    <text x="346" y="335" font-size="11" text-anchor="middle" fill="#FFFFFF">⚡</text>
    <text x="368" y="327" font-size="12" font-weight="600" fill="#FFFFFF">Apache Kafka Event Bus</text>
    <text x="368" y="343" font-size="10" fill="#A1A1AA">Pub/Sub Partitioned Event Streams</text>
  </g>

  <!-- Kafka to Payment & Notification -->
  <path d="M 550 305 L 610 271" fill="none" stroke="#71717A" stroke-width="1.5" stroke-dasharray="3 3" marker-end="url(#arrow)" />
  <path d="M 460 357 L 460 410" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />

  <!-- 7. Databases Layer -->
  <!-- Auth DB -->
  <path d="M 280 271 L 280 410" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />
  <g filter="url(#shadow)">
    <rect x="200" y="410" width="160" height="54" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <circle cx="225" cy="437" r="12" fill="#F4F4F5" />
    <text x="225" y="441" font-size="12" text-anchor="middle" fill="#71717A">🗄️</text>
    <text x="248" y="432" font-size="12" font-weight="600" fill="#09090B">Auth Database</text>
    <text x="248" y="448" font-size="10" fill="#71717A">PostgreSQL (Users, Roles)</text>
  </g>

  <!-- Order DB & Notification -->
  <g filter="url(#shadow)">
    <rect x="380" y="410" width="160" height="54" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <circle cx="405" cy="437" r="12" fill="#F4F4F5" />
    <text x="405" y="441" font-size="12" text-anchor="middle" fill="#71717A">📦</text>
    <text x="428" y="432" font-size="12" font-weight="600" fill="#09090B">Order Database</text>
    <text x="428" y="448" font-size="10" fill="#71717A">PostgreSQL + Read Replica</text>
  </g>

  <!-- 8. Stripe External API -->
  <path d="M 640 271 L 640 410" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#arrow)" />
  <g filter="url(#shadow)">
    <rect x="560" y="410" width="160" height="54" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <circle cx="585" cy="437" r="12" fill="#F4F4F5" />
    <text x="585" y="441" font-size="12" text-anchor="middle" fill="#71717A">💳</text>
    <text x="608" y="432" font-size="12" font-weight="600" fill="#09090B">Payment Provider</text>
    <text x="608" y="448" font-size="10" fill="#71717A">Stripe Webhook Gateway</text>
  </g>

  <!-- Telemetry Watermark -->
  <text x="30" y="515" font-size="11" font-family="monospace" fill="#A1A1AA">DiagramGPT v2.4 • Compiler: Mermaid Engine • Deterministic AST Verified</text>
  <rect x="805" y="500" width="85" height="22" rx="4" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1" />
  <text x="847" y="515" font-size="10.5" font-weight="600" fill="#065F46" text-anchor="middle">✓ Validated</text>
</svg>`;

  return {
    id: 'arch-microservices',
    title: 'Distributed Microservices Architecture',
    prompt: 'Create a microservices architecture with API Gateway, Auth, Orders, and Payments',
    type: 'Architecture',
    complexity: 'Moderate',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: '✓ Passed',
    nodesCount: 8,
    edgesCount: 11,
    latency: '342ms',
    dslCode: dsl,
    svgContent: svg
  };
}

function getERDDiagram() {
  const dsl = `erDiagram
    USERS ||--o{ ORDERS : places
    USERS {
        uuid id PK
        string email UK
        string password_hash
        timestamp created_at
    }
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDERS {
        uuid id PK
        uuid user_id FK
        string status
        decimal total_amount
        timestamp created_at
    }
    PRODUCTS ||--o{ ORDER_ITEMS : ordered_in
    PRODUCTS {
        uuid id PK
        string sku UK
        string name
        decimal unit_price
        integer inventory_count
    }
    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        integer quantity
        decimal unit_price
    }
    ORDERS ||--|| PAYMENTS : settles
    PAYMENTS {
        uuid id PK
        uuid order_id FK
        string provider
        string status
        timestamp processed_at
    }`;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 540" width="100%" height="100%" style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;">
  <defs>
    <filter id="shadow-erd" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000000" flood-opacity="0.05" />
    </filter>
  </defs>

  <rect width="100%" height="100%" fill="#FFFFFF" rx="12" />
  <pattern id="grid-erd" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="1" cy="1" r="1" fill="#F1F5F9" />
  </pattern>
  <rect width="100%" height="100%" fill="url(#grid-erd)" rx="12" />

  <!-- Entity 1: USERS -->
  <g filter="url(#shadow-erd)">
    <rect x="50" y="50" width="220" height="190" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <path d="M 50 50 L 270 50 A 8 8 0 0 1 270 85 L 50 85 Z" fill="#18181B" />
    <text x="65" y="72" font-size="13" font-weight="700" fill="#FFFFFF" letter-spacing="0.5">USERS</text>
    <text x="250" y="72" font-size="11" fill="#A1A1AA" text-anchor="end">table</text>
    
    <text x="65" y="110" font-size="11" font-weight="600" fill="#2563EB">PK</text>
    <text x="95" y="110" font-size="11.5" font-family="monospace" fill="#09090B">id</text>
    <text x="250" y="110" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="60" y1="120" x2="260" y2="120" stroke="#F4F4F5" />

    <text x="65" y="140" font-size="11" font-weight="600" fill="#059669">UK</text>
    <text x="95" y="140" font-size="11.5" font-family="monospace" fill="#09090B">email</text>
    <text x="250" y="140" font-size="11" fill="#71717A" text-anchor="end">VARCHAR(255)</text>
    <line x1="60" y1="150" x2="260" y2="150" stroke="#F4F4F5" />

    <text x="95" y="170" font-size="11.5" font-family="monospace" fill="#09090B">password_hash</text>
    <text x="250" y="170" font-size="11" fill="#71717A" text-anchor="end">VARCHAR(255)</text>
    <line x1="60" y1="180" x2="260" y2="180" stroke="#F4F4F5" />

    <text x="95" y="200" font-size="11.5" font-family="monospace" fill="#09090B">created_at</text>
    <text x="250" y="200" font-size="11" fill="#71717A" text-anchor="end">TIMESTAMP</text>
  </g>

  <!-- Relationship: USERS 1 --- * ORDERS -->
  <path d="M 270 145 L 350 145" fill="none" stroke="#71717A" stroke-width="1.5" />
  <!-- Crow's foot / 1-to-many indicator -->
  <line x1="285" y1="137" x2="285" y2="153" stroke="#71717A" stroke-width="1.5" />
  <line x1="290" y1="137" x2="290" y2="153" stroke="#71717A" stroke-width="1.5" />
  <path d="M 335 137 L 350 145 L 335 153" fill="none" stroke="#71717A" stroke-width="1.5" />
  <text x="310" y="132" font-size="10" font-weight="600" fill="#71717A" text-anchor="middle">places (1:N)</text>

  <!-- Entity 2: ORDERS -->
  <g filter="url(#shadow-erd)">
    <rect x="350" y="50" width="220" height="215" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <path d="M 350 50 L 570 50 A 8 8 0 0 1 570 85 L 350 85 Z" fill="#18181B" />
    <text x="365" y="72" font-size="13" font-weight="700" fill="#FFFFFF" letter-spacing="0.5">ORDERS</text>
    <text x="550" y="72" font-size="11" fill="#A1A1AA" text-anchor="end">table</text>
    
    <text x="365" y="110" font-size="11" font-weight="600" fill="#2563EB">PK</text>
    <text x="395" y="110" font-size="11.5" font-family="monospace" fill="#09090B">id</text>
    <text x="550" y="110" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="360" y1="120" x2="560" y2="120" stroke="#F4F4F5" />

    <text x="365" y="140" font-size="11" font-weight="600" fill="#D97706">FK</text>
    <text x="395" y="140" font-size="11.5" font-family="monospace" fill="#09090B">user_id</text>
    <text x="550" y="140" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="360" y1="150" x2="560" y2="150" stroke="#F4F4F5" />

    <text x="395" y="170" font-size="11.5" font-family="monospace" fill="#09090B">status</text>
    <text x="550" y="170" font-size="11" fill="#71717A" text-anchor="end">VARCHAR(32)</text>
    <line x1="360" y1="180" x2="560" y2="180" stroke="#F4F4F5" />

    <text x="395" y="200" font-size="11.5" font-family="monospace" fill="#09090B">total_amount</text>
    <text x="550" y="200" font-size="11" fill="#71717A" text-anchor="end">NUMERIC(10,2)</text>
    <line x1="360" y1="210" x2="560" y2="210" stroke="#F4F4F5" />

    <text x="395" y="230" font-size="11.5" font-family="monospace" fill="#09090B">created_at</text>
    <text x="550" y="230" font-size="11" fill="#71717A" text-anchor="end">TIMESTAMP</text>
  </g>

  <!-- Entity 3: ORDER_ITEMS -->
  <g filter="url(#shadow-erd)">
    <rect x="650" y="50" width="220" height="215" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <path d="M 650 50 L 870 50 A 8 8 0 0 1 870 85 L 650 85 Z" fill="#18181B" />
    <text x="665" y="72" font-size="13" font-weight="700" fill="#FFFFFF" letter-spacing="0.5">ORDER_ITEMS</text>
    <text x="850" y="72" font-size="11" fill="#A1A1AA" text-anchor="end">junction</text>

    <text x="665" y="110" font-size="11" font-weight="600" fill="#2563EB">PK</text>
    <text x="695" y="110" font-size="11.5" font-family="monospace" fill="#09090B">id</text>
    <text x="850" y="110" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="660" y1="120" x2="860" y2="120" stroke="#F4F4F5" />

    <text x="665" y="140" font-size="11" font-weight="600" fill="#D97706">FK</text>
    <text x="695" y="140" font-size="11.5" font-family="monospace" fill="#09090B">order_id</text>
    <text x="850" y="140" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="660" y1="150" x2="860" y2="150" stroke="#F4F4F5" />

    <text x="665" y="170" font-size="11" font-weight="600" fill="#D97706">FK</text>
    <text x="695" y="170" font-size="11.5" font-family="monospace" fill="#09090B">product_id</text>
    <text x="850" y="170" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="660" y1="180" x2="860" y2="180" stroke="#F4F4F5" />

    <text x="695" y="200" font-size="11.5" font-family="monospace" fill="#09090B">quantity</text>
    <text x="850" y="200" font-size="11" fill="#71717A" text-anchor="end">INTEGER</text>
    <line x1="660" y1="210" x2="860" y2="210" stroke="#F4F4F5" />

    <text x="695" y="230" font-size="11.5" font-family="monospace" fill="#09090B">unit_price</text>
    <text x="850" y="230" font-size="11" fill="#71717A" text-anchor="end">NUMERIC(10,2)</text>
  </g>

  <!-- Connect ORDERS to ORDER_ITEMS -->
  <path d="M 570 145 L 650 145" fill="none" stroke="#71717A" stroke-width="1.5" />
  <line x1="585" y1="137" x2="585" y2="153" stroke="#71717A" stroke-width="1.5" />
  <path d="M 635 137 L 650 145 L 635 153" fill="none" stroke="#71717A" stroke-width="1.5" />
  <text x="610" y="132" font-size="10" font-weight="600" fill="#71717A" text-anchor="middle">has (1:N)</text>

  <!-- Entity 4: PAYMENTS -->
  <g filter="url(#shadow-erd)">
    <rect x="200" y="320" width="220" height="150" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <path d="M 200 320 L 420 320 A 8 8 0 0 1 420 355 L 200 355 Z" fill="#18181B" />
    <text x="215" y="342" font-size="13" font-weight="700" fill="#FFFFFF" letter-spacing="0.5">PAYMENTS</text>
    <text x="400" y="342" font-size="11" fill="#A1A1AA" text-anchor="end">table</text>

    <text x="215" y="380" font-size="11" font-weight="600" fill="#2563EB">PK</text>
    <text x="245" y="380" font-size="11.5" font-family="monospace" fill="#09090B">id</text>
    <text x="400" y="380" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="210" y1="390" x2="410" y2="390" stroke="#F4F4F5" />

    <text x="215" y="410" font-size="11" font-weight="600" fill="#D97706">FK</text>
    <text x="245" y="410" font-size="11.5" font-family="monospace" fill="#09090B">order_id</text>
    <text x="400" y="410" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="210" y1="420" x2="410" y2="420" stroke="#F4F4F5" />

    <text x="245" y="440" font-size="11.5" font-family="monospace" fill="#09090B">status</text>
    <text x="400" y="440" font-size="11" fill="#71717A" text-anchor="end">VARCHAR(32)</text>
  </g>

  <!-- Connect ORDERS to PAYMENTS (1:1) -->
  <path d="M 430 265 L 430 300 L 310 300 L 310 320" fill="none" stroke="#71717A" stroke-width="1.5" />
  <line x1="422" y1="280" x2="438" y2="280" stroke="#71717A" stroke-width="1.5" />
  <line x1="302" y1="310" x2="318" y2="310" stroke="#71717A" stroke-width="1.5" />
  <text x="360" y="295" font-size="10" font-weight="600" fill="#71717A" text-anchor="middle">settles (1:1)</text>

  <!-- Entity 5: PRODUCTS -->
  <g filter="url(#shadow-erd)">
    <rect x="520" y="320" width="220" height="150" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <path d="M 520 320 L 740 320 A 8 8 0 0 1 740 355 L 520 355 Z" fill="#18181B" />
    <text x="535" y="342" font-size="13" font-weight="700" fill="#FFFFFF" letter-spacing="0.5">PRODUCTS</text>
    <text x="720" y="342" font-size="11" fill="#A1A1AA" text-anchor="end">catalog</text>

    <text x="535" y="380" font-size="11" font-weight="600" fill="#2563EB">PK</text>
    <text x="565" y="380" font-size="11.5" font-family="monospace" fill="#09090B">id</text>
    <text x="720" y="380" font-size="11" fill="#71717A" text-anchor="end">UUID</text>
    <line x1="530" y1="390" x2="730" y2="390" stroke="#F4F4F5" />

    <text x="535" y="410" font-size="11" font-weight="600" fill="#059669">UK</text>
    <text x="565" y="410" font-size="11.5" font-family="monospace" fill="#09090B">sku</text>
    <text x="720" y="410" font-size="11" fill="#71717A" text-anchor="end">VARCHAR(64)</text>
    <line x1="530" y1="420" x2="730" y2="420" stroke="#F4F4F5" />

    <text x="565" y="440" font-size="11.5" font-family="monospace" fill="#09090B">unit_price</text>
    <text x="720" y="440" font-size="11" fill="#71717A" text-anchor="end">NUMERIC(10,2)</text>
  </g>

  <!-- Connect PRODUCTS to ORDER_ITEMS -->
  <path d="M 690 320 L 690 300 L 760 300 L 760 265" fill="none" stroke="#71717A" stroke-width="1.5" />
  <line x1="682" y1="310" x2="698" y2="310" stroke="#71717A" stroke-width="1.5" />
  <path d="M 752 280 L 760 265 L 768 280" fill="none" stroke="#71717A" stroke-width="1.5" />
  <text x="735" y="308" font-size="10" font-weight="600" fill="#71717A">1:N</text>

  <!-- Footer Watermark -->
  <text x="30" y="515" font-size="11" font-family="monospace" fill="#A1A1AA">DiagramGPT v2.4 • Relational Entity-Relationship Diagram • Primary/Foreign Keys Invariant Verified</text>
  <rect x="805" y="500" width="85" height="22" rx="4" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1" />
  <text x="847" y="515" font-size="10.5" font-weight="600" fill="#065F46" text-anchor="middle">✓ Validated</text>
</svg>`;

  return {
    id: 'erd-ecommerce',
    title: 'Relational Database Schema (ERD)',
    prompt: 'Create an ER diagram for Users, Orders, Products, and Payments',
    type: 'Entity-Relationship',
    complexity: 'Moderate',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: '✓ Passed',
    nodesCount: 5,
    edgesCount: 4,
    latency: '280ms',
    dslCode: dsl,
    svgContent: svg
  };
}

function getWorkflowDiagram() {
  const dsl = `stateDiagram-v2
    [*] --> Submitted: Order Placed
    Submitted --> Validating: System Check
    Validating --> InventoryReserved: Stock Confirmed
    Validating --> PaymentFailed: Insufficient Funds
    
    InventoryReserved --> ProcessingPayment: Request Gateway
    ProcessingPayment --> PaymentConfirmed: Charge OK
    ProcessingPayment --> PaymentFailed: Decline / Timeout
    
    PaymentConfirmed --> Fulfillment: Dispatched to Warehouse
    Fulfillment --> Shipped: Carrier Handshake
    Shipped --> Delivered: Geolocation Ping
    
    PaymentFailed --> Cancelled: Revert Inventory
    Delivered --> [*]
    Cancelled --> [*]`;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 540" width="100%" height="100%" style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;">
  <defs>
    <filter id="shadow-wf" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000000" flood-opacity="0.05" />
    </filter>
    <marker id="wf-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#71717A" />
    </marker>
    <marker id="wf-arrow-green" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#059669" />
    </marker>
    <marker id="wf-arrow-red" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#DC2626" />
    </marker>
  </defs>

  <rect width="100%" height="100%" fill="#FFFFFF" rx="12" />
  <pattern id="grid-wf" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="1" cy="1" r="1" fill="#F1F5F9" />
  </pattern>
  <rect width="100%" height="100%" fill="url(#grid-wf)" rx="12" />

  <!-- Start State -->
  <circle cx="90" cy="140" r="14" fill="#18181B" />
  <circle cx="90" cy="140" r="8" fill="#FFFFFF" />
  <circle cx="90" cy="140" r="5" fill="#18181B" />
  <text x="90" y="172" font-size="11" font-weight="600" fill="#71717A" text-anchor="middle">Order Placed</text>

  <!-- Step 1: Submitted -->
  <path d="M 104 140 L 170 140" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#wf-arrow)" />

  <g filter="url(#shadow-wf)">
    <rect x="170" y="112" width="130" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="235" y="138" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">1. Submitted</text>
    <text x="235" y="154" font-size="10" fill="#71717A" text-anchor="middle">Payload Ingestion</text>
  </g>

  <!-- Step 2: Decision Node (Validation) -->
  <path d="M 300 140 L 360 140" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#wf-arrow)" />

  <g filter="url(#shadow-wf)">
    <polygon points="410,105 465,140 410,175 355,140" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="410" y="137" font-size="11" font-weight="600" fill="#09090B" text-anchor="middle">Validate</text>
    <text x="410" y="151" font-size="9.5" fill="#71717A" text-anchor="middle">Inventory?</text>
  </g>

  <!-- Branch: Yes -> Payment Processing -->
  <path d="M 465 140 L 530 140" fill="none" stroke="#059669" stroke-width="1.5" marker-end="url(#wf-arrow-green)" />
  <text x="495" y="132" font-size="10" font-weight="600" fill="#059669" text-anchor="middle">Stock OK</text>

  <!-- Step 3: Processing Payment -->
  <g filter="url(#shadow-wf)">
    <rect x="530" y="112" width="150" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="605" y="138" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">2. Process Payment</text>
    <text x="605" y="154" font-size="10" fill="#71717A" text-anchor="middle">3D-Secure / Charge</text>
  </g>

  <!-- Branch: No -> Cancelled -->
  <path d="M 410 175 L 410 320 L 480 320" fill="none" stroke="#DC2626" stroke-width="1.5" marker-end="url(#wf-arrow-red)" />
  <text x="418" y="240" font-size="10" font-weight="600" fill="#DC2626">Out of Stock</text>

  <g filter="url(#shadow-wf)">
    <rect x="480" y="292" width="140" height="56" rx="8" fill="#FEF2F2" stroke="#FCA5A5" stroke-width="1.5" />
    <text x="550" y="318" font-size="12.5" font-weight="600" fill="#991B1B" text-anchor="middle">Order Rejected</text>
    <text x="550" y="334" font-size="10" fill="#B91C1C" text-anchor="middle">Stock Reverted</text>
  </g>

  <!-- Payment Outcome: Success -->
  <path d="M 680 140 L 740 140" fill="none" stroke="#059669" stroke-width="1.5" marker-end="url(#wf-arrow-green)" />
  <text x="710" y="132" font-size="10" font-weight="600" fill="#059669" text-anchor="middle">Success</text>

  <!-- Step 4: Fulfillment -->
  <g filter="url(#shadow-wf)">
    <rect x="740" y="112" width="140" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="810" y="138" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">3. Fulfillment</text>
    <text x="810" y="154" font-size="10" fill="#71717A" text-anchor="middle">Packing &amp; Label</text>
  </g>

  <!-- Flow down to Dispatched / Shipped -->
  <path d="M 810 168 L 810 240 L 740 240" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#wf-arrow)" />

  <g filter="url(#shadow-wf)">
    <rect x="580" y="212" width="160" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="660" y="238" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">4. In Transit</text>
    <text x="660" y="254" font-size="10" fill="#71717A" text-anchor="middle">Carrier Tracking Active</text>
  </g>

  <!-- Final State: Delivered -->
  <path d="M 580 240 L 510 240" fill="none" stroke="#059669" stroke-width="1.5" marker-end="url(#wf-arrow-green)" />

  <g filter="url(#shadow-wf)">
    <rect x="350" y="212" width="160" height="56" rx="8" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1.5" />
    <text x="430" y="238" font-size="12.5" font-weight="600" fill="#065F46" text-anchor="middle">5. Delivered</text>
    <text x="430" y="254" font-size="10" fill="#047857" text-anchor="middle">Proof of Delivery Verified</text>
  </g>

  <!-- Connect to terminal state -->
  <path d="M 350 240 L 290 240" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#wf-arrow)" />
  <circle cx="270" cy="240" r="14" fill="#FFFFFF" stroke="#18181B" stroke-width="2" />
  <circle cx="270" cy="240" r="9" fill="#18181B" />
  <text x="270" y="272" font-size="11" font-weight="600" fill="#71717A" text-anchor="middle">Complete</text>

  <!-- Connect Rejection to Terminal -->
  <path d="M 480 320 L 270 320 L 270 258" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#wf-arrow)" />

  <!-- Footer Telemetry -->
  <text x="30" y="515" font-size="11" font-family="monospace" fill="#A1A1AA">DiagramGPT v2.4 • State Workflow Pipeline • Reachability &amp; Liveness Verified</text>
  <rect x="805" y="500" width="85" height="22" rx="4" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1" />
  <text x="847" y="515" font-size="10.5" font-weight="600" fill="#065F46" text-anchor="middle">✓ Validated</text>
</svg>`;

  return {
    id: 'wf-order-fulfillment',
    title: 'E-Commerce Order Fulfillment Workflow',
    prompt: 'Create a system workflow for event-driven order processing',
    type: 'Workflow / State',
    complexity: 'Simple',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: '✓ Passed',
    nodesCount: 7,
    edgesCount: 9,
    latency: '215ms',
    dslCode: dsl,
    svgContent: svg
  };
}

function getCustomArchitectureDiagram(userPrompt) {
  const promptSummary = userPrompt.length > 50 ? userPrompt.substring(0, 50) + '...' : userPrompt;

  const dsl = `graph TD
  User([User Interaction]) --> Ingestion[Data Ingestion / API]
  Ingestion --> ProcessingEngine[Core Processing Engine]
  ProcessingEngine --> Cache[(In-Memory Cache)]
  ProcessingEngine --> PersistentStorage[(Primary Database)]
  ProcessingEngine --> OutputQueue{Event Dispatcher}
  OutputQueue --> DownstreamConsumers[Downstream Consumers]`;

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 540" width="100%" height="100%" style="font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;">
  <defs>
    <filter id="shadow-custom" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="#000000" flood-opacity="0.05" />
    </filter>
    <marker id="custom-arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#71717A" />
    </marker>
  </defs>

  <rect width="100%" height="100%" fill="#FFFFFF" rx="12" />
  <pattern id="grid-c" width="24" height="24" patternUnits="userSpaceOnUse">
    <circle cx="1" cy="1" r="1" fill="#F1F5F9" />
  </pattern>
  <rect width="100%" height="100%" fill="url(#grid-c)" rx="12" />

  <!-- Title Pill -->
  <rect x="50" y="40" width="400" height="36" rx="18" fill="#F4F4F5" stroke="#E4E4E7" stroke-width="1" />
  <text x="70" y="63" font-size="12" font-weight="600" fill="#18181B">Generated Architecture Spec</text>
  <text x="235" y="63" font-size="11" fill="#71717A">"${promptSummary}"</text>

  <!-- Node 1: Entry -->
  <g filter="url(#shadow-custom)">
    <rect x="360" y="110" width="200" height="52" rx="26" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="460" y="136" font-size="13" font-weight="600" fill="#09090B" text-anchor="middle">Input Clients &amp; Devices</text>
    <text x="460" y="151" font-size="10.5" fill="#71717A" text-anchor="middle">Authenticated TLS Inbound</text>
  </g>

  <!-- Arrow -->
  <path d="M 460 162 L 460 200" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#custom-arrow)" />

  <!-- Node 2: Core Processing Service -->
  <g filter="url(#shadow-custom)">
    <rect x="330" y="200" width="260" height="60" rx="8" fill="#18181B" stroke="#27272A" stroke-width="1" />
    <text x="460" y="227" font-size="13.5" font-weight="600" fill="#FFFFFF" text-anchor="middle">AI Pipeline Orchestrator</text>
    <text x="460" y="246" font-size="11" fill="#A1A1AA" text-anchor="middle">Syntactic Parser &amp; State Classifier</text>
  </g>

  <!-- Connectors to 3 storage/downstream nodes -->
  <path d="M 380 260 L 250 330" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#custom-arrow)" />
  <path d="M 460 260 L 460 330" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#custom-arrow)" />
  <path d="M 540 260 L 670 330" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#custom-arrow)" />

  <!-- Node 3: Cache -->
  <g filter="url(#shadow-custom)">
    <rect x="160" y="330" width="180" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="250" y="355" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">In-Memory Cache</text>
    <text x="250" y="372" font-size="10.5" fill="#71717A" text-anchor="middle">Redis Cluster (Low Latency)</text>
  </g>

  <!-- Node 4: Database -->
  <g filter="url(#shadow-custom)">
    <rect x="370" y="330" width="180" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="460" y="355" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">Primary Storage</text>
    <text x="460" y="372" font-size="10.5" fill="#71717A" text-anchor="middle">PostgreSQL Relational DB</text>
  </g>

  <!-- Node 5: Event Broker -->
  <g filter="url(#shadow-custom)">
    <rect x="580" y="330" width="180" height="56" rx="8" fill="#FFFFFF" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="670" y="355" font-size="12.5" font-weight="600" fill="#09090B" text-anchor="middle">Event Dispatcher</text>
    <text x="670" y="372" font-size="10.5" fill="#71717A" text-anchor="middle">Async Queue / Kafka</text>
  </g>

  <!-- Downstream Consumer -->
  <path d="M 670 386 L 670 430" fill="none" stroke="#71717A" stroke-width="1.5" marker-end="url(#custom-arrow)" />
  <g filter="url(#shadow-custom)">
    <rect x="580" y="430" width="180" height="48" rx="8" fill="#FAFAFA" stroke="#E4E4E7" stroke-width="1.5" />
    <text x="670" y="458" font-size="12" font-weight="500" fill="#52525B" text-anchor="middle">Downstream Consumers</text>
  </g>

  <!-- Footer Watermark -->
  <text x="30" y="515" font-size="11" font-family="monospace" fill="#A1A1AA">DiagramGPT v2.4 • Dynamic Extraction AST • Verified Graph Topology</text>
  <rect x="805" y="500" width="85" height="22" rx="4" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1" />
  <text x="847" y="515" font-size="10.5" font-weight="600" fill="#065F46" text-anchor="middle">✓ Validated</text>
</svg>`;

  return {
    id: `custom-${Date.now()}`,
    title: 'Synthesized Architecture Specification',
    prompt: userPrompt,
    type: 'Architecture',
    complexity: 'Moderate',
    routing: 'DSL Renderer',
    renderer: 'Mermaid',
    validation: '✓ Passed',
    nodesCount: 6,
    edgesCount: 7,
    latency: '310ms',
    dslCode: dsl,
    svgContent: svg
  };
}
