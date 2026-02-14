# SEVABOT Infrastructure & Technology Stack Decisions

## Executive Summary

This document justifies technology choices for SEVABOT considering:
- **Constraints:** Limited budget, team size, initial user base
- **Scalability:** Path from 10 to 1000 users without major refactoring
- **Resource efficiency:** Minimal operational overhead
- **Total Cost of Ownership (TCO):** Balance between cost and features

---

## Technology Stack Breakdown

### 1. Web Framework: FastAPI

**Choice:** FastAPI (Python async framework)

**Justification:**

| Criterion | FastAPI | Django | Node.js |
|-----------|---------|--------|---------|
| **Setup time** | <1 hour | 2+ hours | 30 min |
| **Learning curve** | Moderate | Steep | Easy |
| **Python integration** | ✅ Native | ✅ Native | ❌ Requires bridge |
| **Async support** | ✅ Built-in | ⚠️ Complex | ✅ Native |
| **Auto-docs** | ✅ Swagger/OpenAPI | ❌ Manual | ⚠️ Manual |
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Dependencies** | Minimal | Heavy | Moderate |

**Why not others:**
- **Django:** Overkill for RAG app; heavy monolith for small team
- **Node.js:** Would require bridges to Python ML libraries (LangChain, ChromaDB)
- **Go:** Better performance, but team expertise in Python

**Cost Impact:** Development time savings = 20+ hours over project lifespan

---

### 2. UI Framework: Gradio

**Choice:** Gradio 4.x for web interface

**Justification:**

| Criterion | Gradio | Streamlit | Custom React |
|-----------|--------|-----------|--------------|
| **Setup time** | <30 min | <30 min | 5+ hours |
| **Auth support** | ✅ Manual OK | ⚠️ Limited | ✅ Full control |
| **File upload** | ✅ Built-in | ✅ Built-in | ⚠️ Manual impl |
| **Admin features** | ✅ Custom | ⚠️ Limited | ✅ Full control |
| **Hosting** | Any server | Streamlit Cloud/Docker | Any server |
| **Team expertise** | Python only | Python only | Requires frontend dev |
| **Mobile support** | ⚠️ Responsive | ⚠️ Responsive | ✅ Full |

**Why Gradio over alternatives:**
- **Streamlit:** Works for prototypes; complex admin features difficult
- **Custom React:** Requires frontend developers (costly for small team)
- **Gradio sweet spot:** Python-first, rapid UI development, enough customization for admin panel

**Cost Impact:** Eliminates need for separate frontend developer

**Trade-offs:**
- Less control over UI design (acceptable for internal tool)
- Mobile not optimized (OK for desktop-first use case)

---

### 3. Vector Database: ChromaDB

**Choice:** ChromaDB (in-memory + persistent)

**Justification:**

| Criterion | ChromaDB | Pinecone | Weaviate | Milvus |
|-----------|----------|----------|----------|--------|
| **Hosting** | Self-hosted | SaaS | Self/Cloud | Self-hosted |
| **Cost (free tier)** | ✅ Unlimited | ⚠️ Limited | ✅ Free | ✅ Free |
| **Setup complexity** | ⭐ Easy | ⭐ Easy (cloud) | ⭐⭐ Medium | ⭐⭐⭐ Hard |
| **Performance** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Scalability** | Up to 10M vectors | Unlimited | Large scale | Large scale |
| **Operational cost** | Low | High | Medium | Low |
| **Multi-tenancy** | ✅ Collections | ✅ Indexes | ✅ Namespaces | ✅ Collections |

**Why ChromaDB:**
- **Zero cost:** No monthly SaaS bill for initial phase
- **Simplicity:** Drop-in replacement, no DevOps complexity
- **Sufficient for our scale:** 100K documents × 5 chunks = 500K vectors (well within limits)
- **Easy migration path:** Can switch to Pinecone if we hit limits

**Scaling path:**
- **Phase 1 (Current):** ChromaDB in-process (~100K vectors)
- **Phase 2 (10M vectors):** ChromaDB + persistent file storage or Milvus
- **Phase 3 (100M+ vectors):** Pinecone or Weaviate (managed cloud)

**Cost Analysis:**

| Phase | Users | Vectors | ChromaDB Cost | Pinecone Cost |
|-------|-------|---------|---------------|---------------|
| **Current** | 100 | 500K | Free | $70/mo (P2 index) |
| **Phase 2** | 500 | 5M | Free (self-hosted) | $500/mo |
| **Phase 3** | 5000 | 50M | Free (self-hosted) | $3000+/mo |

**With ChromaDB:** We avoid $70+/month cost until we genuinely need managed service

---

### 4. Database: Supabase (PostgreSQL)

**Choice:** Supabase (managed PostgreSQL + auth)

**Justification:**

| Criterion | Supabase | Firebase | AWS RDS | Self-Hosted PG |
|-----------|----------|----------|---------|-----------------|
| **Cost (free tier)** | ✅ 500 MB DB | ⚠️ 5 GB | ❌ Paid | ✅ Free (self-hosted) |
| **Auth included** | ✅ Google OAuth | ✅ Google OAuth | ❌ Extra service | ❌ Manual impl |
| **Auto scaling** | ⚠️ Manual | ✅ Auto | ✅ Auto | ❌ Manual |
| **Setup time** | <10 min | <10 min | 30 min | 1+ hour |
| **RLS (Row Security)** | ✅ Built-in | ⚠️ Limited | ✅ Via triggers | ✅ Native |
| **Backup/Recovery** | ✅ Auto | ✅ Auto | ✅ Auto | ⚠️ Manual |
| **Paid tier cost** | $25/mo | $25/mo | $30/mo | $0 (but ops cost) |

**Why Supabase:**
1. **Includes OAuth:** Don't need separate auth service (saves $20/mo)
2. **RLS policies:** Data isolation built-in
3. **Free tier sufficient:** 500MB = ~5M rows of conversation/message data
4. **DX superior:** TypeScript/Postgres familiar to developers
5. **No vendor lock:** Export data anytime to self-hosted PostgreSQL

**Cost at different scales:**

| Scale | Users | Data | Supabase Cost | Firebase Cost | AWS RDS Cost |
|-------|-------|------|---------------|---------------|--------------|
| **Startup** | 100 | 50MB | Free | Free | $50+/mo |
| **Growth** | 1000 | 300MB | $25/mo | $25/mo | $100+/mo |
| **Scale** | 10K | 1.5GB | $300/mo | $300/mo | $300+/mo |

**Supabase wins on cost + included auth**

---

### 5. Deployment: Docker + EC2

**Choice:** Docker containers on AWS EC2 (not Kubernetes/serverless)

**Justification:**

| Criterion | Docker/EC2 | Kubernetes | Lambda/Serverless | PaaS (Heroku) |
|-----------|-----------|-----------|-------------------|---------------|
| **Setup complexity** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ |
| **Operational overhead** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐ |
| **Deployment speed** | <1 min | 5+ min | <30 sec | <1 min |
| **Cost for 24/7 service** | $15-50/mo | $50+/mo | $200+/mo | $50+/mo |
| **Team expertise** | Common | Requires DevOps | Requires AWS expert | Easy |
| **Startup cost** | Low | Medium | High | Medium |
| **Scaling elasticity** | Manual | Auto | Auto | Auto |

**Why Docker + EC2:**
1. **Cost-effective for 24/7:** Single t3.medium = $30/month vs. Heroku $50+
2. **Learning curve:** Team can manage one Docker container easily
3. **No cold starts:** Lambda cold starts = 3-5s penalty (bad for chat UX)
4. **Stateful app:** ChromaDB + document storage needs persistent disk
5. **Simplicity:** One binary decision = Docker, not Kubernetes cluster

**Serverless rejection reasons:**
- ChromaDB needs persistent file system (not suitable for Lambda)
- Chat responses take seconds (Lambda cold starts compound this)
- Long-running document processing (Lambda 15min timeout)
- Cost jumps significantly with continuous traffic

**Kubernetes rejection reasons:**
- Overkill for single-digit traffic initially
- Requires DevOps expertise (small team doesn't have)
- Minimum 3-node cluster = $100+/month
- Complexity isn't needed until 1000+ concurrent users

**Evolution path:**
1. **Phase 1 (Current):** Docker on t3.medium EC2 ($30/mo)
2. **Phase 2 (100 users):** Still single container (scale up to t3.large = $60/mo)
3. **Phase 3 (1000 users):** Multi-container Docker Compose or Kubernetes
4. **Phase 4 (10K users):** Kubernetes on EKS

---

### 6. Reverse Proxy: Nginx

**Choice:** Nginx (not managed load balancer)

**Justification:**

For single EC2 instance, Nginx is sufficient:
- ✅ TLS termination (HTTPS)
- ✅ Reverse proxy to FastAPI
- ✅ Static file serving
- ✅ Request buffering (file uploads)
- ✅ WebSocket support (Gradio)
- ✅ Zero cost (installed on EC2)

**When to upgrade:**
- **Multi-instance (future):** AWS Application Load Balancer (ALB) = $20/month
- **DDoS protection:** Cloudflare DDoS = $200/month

---

### 7. LLM: OpenAI (GPT-4o)

**Choice:** OpenAI API (not local LLM, not Anthropic Claude)

**Justification:**

| Criterion | OpenAI GPT-4o | Local Llama | Anthropic Claude |
|-----------|---------------|-------------|------------------|
| **Setup** | API key only | Local GPU needed | API key only |
| **Cost per 1M tokens** | $5 (input) / $15 (output) | $0 (but GPU cost) | $3 / $15 |
| **Performance** | Best | Good | Best |
| **Latency** | 2-5s | Instant | 2-5s |
| **Infra cost** | $0 | GPU = $200+/mo | $0 |
| **Token efficiency** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**Why OpenAI over local LLM:**
1. **No GPU needed:** Would require GPU EC2 instance = $300+/month
2. **Better quality:** GPT-4o > open-source Llama for complex queries
3. **Cost predictable:** Pay per token, no infrastructure costs
4. **Faster deployment:** No model setup or optimization needed

**Cost at different usage levels:**

| Usage | Requests/day | Input tokens/day | Output tokens/day | Monthly Cost |
|-------|--------------|-----------------|------------------|--------------|
| **Light** | 100 | 1M | 500K | $10 |
| **Medium** | 500 | 5M | 2.5M | $40 |
| **Heavy** | 2000 | 20M | 10M | $160 |

**Formula:** (input_tokens × $5 + output_tokens × $15) / 1,000,000

For typical RAG queries (500 input tokens, 200 output tokens):
- Cost per query = (500 × $5 + 200 × $15) / 1M = $0.005 per query
- 1000 queries/day = $5/day = $150/month

---

### 8. Storage: AWS S3

**Choice:** S3 for document storage (enables scaling)

**Justification:**

| Aspect | Local Storage | S3 |
|--------|---------------|-----|
| **Cost per GB** | $0.10/GB (EC2 disk) | $0.023/GB (S3) |
| **Scalability** | 30GB max (EC2 limit) | Unlimited |
| **Availability** | Single AZ | Multi-AZ redundant |
| **Backup** | Manual | Versioning built-in |
| **Setup** | None needed | Enable S3 option |
| **Network cost** | Included | $0.01/GB (out) |

**When S3 is worth it:**
- **>10GB documents:** S3 cheaper than EC2 storage
- **Multi-region needs:** S3 easier to manage
- **Backup requirements:** S3 versioning automatic
- **Archive conversations:** S3 ideal for long-term storage

**Current cost:**
- 100 users × 10 MB docs = 1 GB = **$0.02/month** (negligible)
- Network egress (downloads) = **$0.01 per 100 downloads**

**Scaling path:**
- **Phase 1 (Now):** Local EC2 storage + enable S3 option
- **Phase 2 (1GB docs):** Migrate to S3 (cost neutral)
- **Phase 3 (100GB docs):** S3 becomes clear win

**Current recommendation:** Enable S3 in code, but use local storage. When we hit 30GB, flip a config flag to S3 with zero code changes.

---

## Total Cost of Ownership (TCO) Analysis

### Current Phase (100 users)

| Component | Cost/Month | Notes |
|-----------|-----------|-------|
| **EC2 (t3.medium)** | $30 | Compute + storage |
| **Supabase (free tier)** | $0 | 500 MB DB included |
| **OpenAI API** | $50-150 | $0.005/query |
| **S3 storage** | <$1 | 1GB documents |
| **Domain (optional)** | $12 | `.org` domain |
| **SSL certificate** | $0 | LetsEncrypt free |
| **Monitoring** | $0 | CloudWatch free |
| **CDN (optional)** | $0 | Not needed yet |
| **TOTAL** | **$92-192** | 30% margin to ops |

### Growth Phase (500 users)

| Component | Cost/Month | Change |
|-----------|-----------|--------|
| **EC2 (t3.large)** | $60 | Up from $30 |
| **Supabase (Pro)** | $25 | Growing data |
| **OpenAI API** | $250 | 5× usage |
| **S3 storage** | $2 | 10 GB data |
| **Other** | $12 | Domain, etc |
| **TOTAL** | **$349** | 4× cost, 5× users |

### Scale Phase (5000+ users)

| Component | Cost/Month | Change |
|-----------|-----------|--------|
| **EC2 (2× t3.large)** | $120 | Redundancy |
| **ALB** | $20 | Load balancer |
| **Supabase (Enterprise)** | $200 | $200 base |
| **OpenAI API** | $2000 | 10,000 queries/day |
| **S3 storage** | $20 | 1 TB documents |
| **RDS (backup)** | $100 | Database replication |
| **TOTAL** | **$2460** | 7× cost, 50× users |

---

## Key Decision Trade-offs

### Trade-off 1: Custom Frontend vs. Gradio

**Decision:** Gradio (faster to market)

**Cost saved:** 200+ development hours

**Trade-off:** Less design control
- **Acceptable because:** Internal tool, not customer-facing design
- **Upgrade path:** If needed, keep Gradio UI but add custom React dashboard layer

---

### Trade-off 2: Managed vs. Self-Hosted

**Decision:** Managed services where cost-neutral (Supabase)

**Saved:** Auth server setup, database administration

**Trade-off:** Vendor lock-in risk
- **Mitigation:** Data stays in standard PostgreSQL, exportable anytime
- **Escape hatch:** Migrate to RDS with zero code changes

---

### Trade-off 3: ChatGPT API vs. Local LLM

**Decision:** OpenAI API (remove GPU requirement)

**Cost saved:** $200+/month on GPU infrastructure

**Trade-off:** Dependent on external API
- **Mitigation:** Cache responses, batch requests, fallback to cheaper models if needed
- **Upgrade path:** Add local Llama fallback for cost control at scale

---

### Trade-off 4: Single Container vs. Kubernetes

**Decision:** Docker + EC2 (simpler)

**Cost saved:** $70+/month Kubernetes overhead, DevOps expertise

**Trade-off:** Manual scaling until 1000+ users
- **Acceptable because:** Growth is gradual, manual scaling is simple
- **Upgrade path:** Kubernetes when we have DevOps engineer on team

---

## Cost Optimization Opportunities

### Immediate (No code change)
1. **Spot EC2 instances:** Save 70% (~$20/mo)
   - Risk: Instance can be reclaimed (10% probability)
   - Suitable for: Non-critical environments
2. **Reserved instances (1-year):** Save 30% ($9/mo)
   - Need: Commitment to continuous operation
   - ROI: Breakeven at 4 months

### Short-term (Code changes)
1. **Batch OpenAI requests:** Save 20% on API calls
2. **Cache query responses:** Save 30% on repeated questions
3. **Lazy load documents:** Only index frequently used docs
4. **Compress S3 objects:** Save 50% on storage

### Medium-term (Infrastructure)
1. **Multi-region:** Serve from user's region (CDN)
2. **Database read replicas:** Scale read-heavy queries
3. **Vector DB caching:** Reduce embedding calls
4. **Model fine-tuning:** Use cheaper base model with fine-tuned layer

---

## Recommended Actions

### ✅ Do Now
- [x] Deploy on t3.medium EC2 (costs $30/month)
- [x] Use Supabase free tier (no cost)
- [x] Use OpenAI API (variable cost, no upfront)
- [x] Use local storage + S3 option (flexible)
- [x] Monitor costs weekly

### ⏳ Do When Hitting Limits
- [ ] Switch to t3.large if CPU > 70% for 1 week
- [ ] Enable S3 if EC2 storage > 25GB
- [ ] Upgrade Supabase if > 450MB data
- [ ] Add CloudFlare if > 1Gbps traffic

### 🚀 Do Before 1000 Users
- [ ] Set up Kubernetes cluster
- [ ] Implement caching layer (Redis)
- [ ] Replicate database for read-heavy queries
- [ ] Consider: Local LLM fallback for cost control

---

## Alternatives Considered (and Rejected)

### AWS Amplify (Rejected)
- **Reason:** Overkill for single-page app; better for mobile apps
- **Cost:** $50+/month vs. $30 EC2
- **Expertise:** Less control than Docker

### Firebase (Rejected)
- **Reason:** Firestore pricing explodes with document writes
- **Cost:** $100+/month at 1000 users vs. $25 Supabase
- **Lock-in:** Harder to migrate from Firestore

### DigitalOcean (Partially considered)
- **Reason:** Slightly cheaper ($5/month droplets) but less mature DevOps
- **Trade-off:** AWS has better support, more services to integrate
- **Recommendation:** Use DigitalOcean if team wants simpler interface

### Hugging Face Spaces (Rejected)
- **Reason:** Designed for demos, not production
- **Limitation:** 24-hour timeout, no persistent storage
- **Use case:** Fine for initial prototype

---

## Conclusion

**Current tech stack is optimal for:**
- ✅ Small team (1-2 engineers)
- ✅ Limited budget ($100-200/month)
- ✅ 100-500 initial users
- ✅ Rapid feature development

**Clear upgrade paths exist for:**
- ✅ Growing to 1000+ users (minimal code changes)
- ✅ Scaling to 10K+ users (planned migration to Kubernetes)
- ✅ Reducing costs (caching, local models, spot instances)

**Risk mitigation:**
- ✅ No vendor lock-in on database (PostgreSQL standard)
- ✅ No GPU requirements (can switch models anytime)
- ✅ Simple infrastructure (can migrate to any cloud)

**Bottom line:** We're paying $92-192/month for a production RAG system. A comparable custom-built solution would cost $50K+ in development, plus $500+/month in operations. Our ROI is excellent.

---

**Last Updated:** January 31, 2026  
**Status:** Complete & Reviewed ✅
