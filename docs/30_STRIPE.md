# STRIPE

## Purpose
This document defines how billing and subscriptions must be handled.

Stripe is the billing provider for the application.

## Billing Model for MVP
The MVP should support subscription-based billing.

Initial target model:
- Free plan
- Pro Monthly plan
- Pro Yearly plan

Do not implement pay-per-action billing in the first version.

## Main Responsibilities of Stripe
Stripe is responsible for:
- checkout
- recurring subscription charging
- customer billing lifecycle
- hosted customer portal if enabled
- subscription events via webhooks

Stripe is not the final authorization layer of the app.
The app must sync relevant billing state into Supabase.

## Billing State Philosophy
Stripe is the billing engine.
Supabase becomes the app-access source of truth after synchronization.

This means:
- payment events happen in Stripe
- application plan state is stored in Supabase
- feature access and quotas depend on synced app state

## Suggested Plan Structure

### Free
Possible example limits:
- limited number of negotiations
- no premium features
- limited history or exports if later added

### Pro Monthly
Possible example:
- recurring monthly subscription
- expanded or unlimited negotiation usage

### Pro Yearly
Possible example:
- recurring yearly subscription
- same feature set as Pro Monthly
- lower effective monthly price

Exact prices are not part of this document.

## Suggested Profile Billing Fields
Store billing-related access state in app data, for example in profiles.

Suggested fields:
- plan
- subscription_status
- stripe_customer_id optional
- stripe_subscription_id optional
- current_period_end optional

The exact schema may vary, but app logic needs a normalized plan/access state.

## Required Flow

### Checkout flow
1. user selects a paid plan
2. app creates Stripe checkout session
3. user completes payment in Stripe
4. Stripe confirms session
5. webhook updates billing state in Supabase

### Renewal flow
1. Stripe renews subscription
2. Stripe sends billing event
3. app updates subscription status in Supabase

### Cancellation / expiry flow
1. subscription is cancelled or expires
2. Stripe emits event
3. app updates access state in Supabase
4. app enforces downgraded access rules

## Webhooks
Webhook handling is mandatory.

At minimum, billing integration should be designed around handling relevant Stripe events.

Typical important events include:
- checkout.session.completed
- customer.subscription.updated
- customer.subscription.deleted
- invoice.paid
- invoice.payment_failed

Do not rely only on redirect success pages for billing state.

## Feature Gating and Limits
Plan checks must not be enforced only in the frontend.

Examples of future gating:
- free users can create at most one negotiation per month
- paid users can create more or unlimited negotiations
- only paid users can access premium features

These checks must be enforced in trusted app logic and backed by database state.

## Customer Portal
If implemented, Stripe customer portal can be used for:
- card updates
- plan changes
- cancellations
- invoice access

This is recommended because it reduces custom billing UI complexity.

## Secrets and Security

Allowed in frontend:
- publishable Stripe key

Allowed only server-side:
- Stripe secret key
- webhook secret

Never expose secret billing credentials in browser code.

## Failure Philosophy
Billing can fail.
The system must be able to represent states such as:
- active
- trialing if introduced later
- past_due
- cancelled
- unpaid if relevant to chosen logic

The app should not assume all paid users are always active forever.

## MVP Billing Simplicity
For the first live MVP:
- keep the plan model simple
- avoid coupons unless needed
- avoid complex seat-based pricing
- avoid usage-based metering
- avoid enterprise custom contracts

## Codex Instructions

Codex must:
- integrate Stripe for subscriptions only
- create checkout flow
- create webhook handling
- synchronize billing state into Supabase
- enforce plan access using backend-synced state

Codex must not:
- trust frontend-only plan checks
- implement pay-per-action billing
- expose Stripe secrets
- make Stripe the only place where access state exists