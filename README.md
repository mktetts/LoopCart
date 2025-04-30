# LoopCart: Transforming the Second-Hand Marketplace

[![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=tPKotTQpgPQ)

## Problem Statement
The second-hand marketplace is plagued by challenges that undermine user trust, engagement, and scalability:
1. **Lack of Trust and Safety**: Fraudulent listings and insecure transactions discourage participation.
2. **Limited Payment Options**: Most platforms support only fiat payments, excluding cryptocurrency users.
3. **Inefficient Product Discovery**: Inadequate search tools and lack of personalized recommendations hinder product discovery.
4. **Restricted Marketing Reach**: Sellers face difficulties promoting listings beyond platform users, limiting buyer acquisition.
5. **Complex Transaction Processes**: In-person purchases and auctions lack streamlined support, reducing user satisfaction.

**LoopCart**, a Salesforce-powered platform with Agentforce integration, addresses these issues by delivering a secure, user-centric, and socially amplified marketplace. LoopCart’s innovative use of **Instagram Posts** for product listings and **Instagram Stories** for product auctions, showcasing how these features enhance marketing reach and user engagement. And LoopCart enables the crypto payments for foreign users.

---

## Inspiration
The idea for LoopCart was born from a commitment to sustainable commerce and the growing popularity of second-hand marketplaces. Inspired by the circular economy movement, which promotes reusing goods to reduce waste, and the power of social media to amplify small-scale sellers, we envisioned a transformative platform. Platforms like eBay and Depop demonstrated the demand for second-hand goods, but their limitations in trust, marketing, and transaction flexibility sparked our vision. We aimed to combine Salesforce’s robust automation with Instagram’s visual storytelling to empower sellers and engage buyers, making second-hand shopping accessible, exciting, and trustworthy.

---

## Project Overview
**LoopCart** is a second-hand marketplace built on Salesforce, leveraging **Agentforce** to provide a seamless and secure buying and selling experience. By integrating advanced automation, geolocation, and social media marketing, LoopCart empowers users to trade pre-owned goods efficiently.

### Key Features
- **Buy/Sell Functionality**: Users can list and purchase second-hand products effortlessly.
- **Flexible Payments**: Supports fiat and cryptocurrency transactions for global accessibility.
- **AI-Driven Recommendations**: Fair comparison algorithm suggests products based on price, condition, and location.
- **Geolocation Search**: Enables buyers to find nearby sellers for in-person purchases.
- **Automated Instagram Marketing**: Agentforce generates Instagram Posts for listings and Stories for auctions.
- **Transparent Dashboards**: Both buyers and sellers track products via Salesforce interfaces.
- **Slack-Based Auctions**: Sellers host real-time auctions by inviting buyers on Slack.

---

## Solution: Instagram-Powered Marketing
LoopCart overcomes the marketing and engagement limitations of traditional second-hand marketplaces by integrating with Instagram, a leading visual platform with over 2 billion active users. Using **Agentforce**, LoopCart automates **Instagram Posts** for product listings and **Instagram Stories** for auctions, driving visibility and interaction.

### 1. Instagram Posts for Product Listings
#### Objective
To amplify the reach of second-hand product listings by promoting them on Instagram, connecting sellers with a broader audience and facilitating local transactions.

#### Implementation
- **Automated Workflow**:
  - Upon listing a product on LoopCart, Agentforce triggers a Salesforce workflow to create an Instagram Post.
  - Product details (images, title, price, condition, location) are extracted from the listing.
  - Salesforce integrates with Instagram’s API to generate and publish the post.
- **Post Composition**:
  - **Visuals**: Up to 9 high-resolution product images for maximum appeal.
  - **Caption**: Concise description by user given description
- **Seller Oversight**:
  - Sellers preview and approve posts via the LoopCart DM.
  - Posts can be published to the  LoopCart’s official account.

#### Impact
- **Broader Reach**: Exposes listings to Instagram’s global audience, increasing buyer interest.
- **Time Efficiency**: Automates marketing, reducing seller effort.
- **Local Engagement**: Geotargeted posts drive in-person transactions, aligning with LoopCart’s nearby search feature.
- **Trust Building**: Professional posts enhance listing credibility.

---

### 2. Instagram Stories for Product Auctions
#### Objective
To create urgency and engagement for time-sensitive auctions, leveraging Instagram Stories’ ephemeral and interactive nature to drive real-time bidding.

#### Implementation
- **Slack-Instagram Integration**:
  - When a seller initiates an auction on LoopCart’s Slack integration, Agentforce generates an Instagram Story.
  - Auction details (product, starting bid, end time) are pulled from the Slack event and formatted for Instagram.
- **Story Composition**:
  - **Visuals**: A single product image or short video, optimized for Stories’ vertical format.
  - **Text Overlay**: Highlights key details (e.g., “Bid on this vintage typewriter! Starts at $75, ends in 4 hours”).

- **Publishing Strategy**:
  - Stories are posted to the LoopCart’s official account.
- **Buyer Access**:
  - Non-Slack users bid via LoopCart’s auction page, while Slack users join dedicated channels for real-time bidding.
  - Agentforce manages Slack invites for seamless participation.

#### Impact
- **Urgency and Excitement**: Stories’ 24-hour lifespan encourages immediate action from bidders.
- **High Engagement**: Interactive stickers boost viewer interaction, increasing auction participation.
- **Seamless Connectivity**: Links bridge Instagram users to LoopCart or Slack, simplifying the bidding process.
- **Scalable Reach**: Official account reposts amplify auction visibility.

---

## Technical Architecture
- **Salesforce Core**:
  - **Agentforce**: Automates workflows for Instagram content creation and auction management.
  - **Data Cloud**: Stores and processes listing/auction data for real-time updates.
  - **Dashboards**: Provide sellers and buyers with transaction and engagement insights.
  - **Methods** : Prompt Templates, Apex code and Flows are used
  - **Data Library**:
    - About LoopCart PDF
    - LoopCart's Terms and conditions PDF
    - TamilNadu cities distance pdf in graph based structure for finding the nearby cities.
    - Refer in Github's page
- **Instagram API**:
  - Handles secure content publishing and retrieves engagement metrics.
  - Adheres to Instagram’s content policies and rate limits.
- **Slack Integration**:
  - Hosts auction channels, with Agentforce managing user invites and notifications.
- **MetaMask**:
  - Please install Metamask from chrome extension.
  - For now, only Gnosis Chiado testnet only supported
  - RPC URL : https://rpc.chiadochain.net
  - Faucet URL : https://faucet.chiadochain.net/
- **FastAPI**
  - FastAPI backend for post to instagram and slack auction bot
  - Deployed in Render

---

## What We Learned
Developing LoopCart provided valuable insights that shaped our approach:
- **Salesforce’s Power**: Agentforce’s automation capabilities enabled rapid development of complex workflows, such as Instagram integration and auction management.
- **Social Media Dynamics**: Instagram’s API constraints taught us to optimize content for compliance while maximizing engagement through hashtags and interactive elements.
- **User-Centric Design**: Feedback loops with mock users highlighted the importance of seller control over automated posts and seamless buyer access to auctions.
- **Cross-Platform Integration**: Combining Salesforce, Instagram, and Slack required careful synchronization to ensure real-time data flow and user experience consistency.
- **Sustainability Focus**: Researching the circular economy reinforced our commitment to building a platform that promotes eco-conscious commerce.

---

## Accomplishments
We are proud of the following achievements during LoopCart’s development:
- **Fully Functional Prototype**: Built a working second-hand marketplace on Salesforce with end-to-end features, including listing, payments, and auctions.
- **Innovative Instagram Integration**: Successfully automated Instagram Posts and Stories using Agentforce, a novel approach to marketplace marketing.
- **Seamless Cross-Platform Experience**: Integrated Salesforce, Instagram, and Slack to create a cohesive user journey from listing to bidding.
- **Crypto Payment Support**: Implemented fiat and cryptocurrency transactions, broadening LoopCart’s accessibility.


---

## Conclusion
LoopCart redefines the second-hand marketplace by addressing critical pain points with a Salesforce-powered, socially amplified solution. The integration of **Instagram Posts** for listings and **Stories** for auctions leverages Agentforce’s automation to enhance marketing reach, user engagement, and transaction efficiency. Inspired by the circular economy and built with cutting-edge technology, LoopCart delivers a scalable, secure, and sustainable platform that empowers users and promotes eco-conscious commerce, making it a standout solution for this hackathon.