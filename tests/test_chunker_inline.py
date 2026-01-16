#!/usr/bin/env python3
"""
Test chunker with inline markdown content.
"""

from chunker import MarkdownChunker

# Test markdown content with headers
test_content = """---
tags: [trading, gold, test]
---

# Gold Market Analysis

This is an introduction to gold markets.

## Market Structure

### Physical Markets

Gold is traded in physical markets around the world. London is the largest center for physical gold trading. The market operates 24 hours through different time zones.

Key participants include:
- Central banks
- Investment funds
- Industrial users
- Retail investors

### Futures Markets

Gold futures are standardized contracts traded on exchanges. The most liquid contract is the COMEX gold futures. These contracts allow for price discovery and hedging.

Contract specifications:
- Size: 100 troy ounces
- Tick size: $0.10 per ounce
- Trading hours: Nearly 24 hours

## Price Drivers

### Real Interest Rates

Real interest rates are the primary driver of gold prices. When real rates fall, gold becomes more attractive as it has no yield. The relationship is inverse and strong.

Historical correlation shows:
- 10-year TIPS yields strongly inverse correlated
- Fed policy changes impact gold significantly
- Inflation expectations matter

### Dollar Strength

The US dollar and gold typically move inversely. A stronger dollar makes gold more expensive for foreign buyers, reducing demand. Currency movements can amplify or dampen other drivers.

## Trading Strategies

### Carry Trades

In gold, carry trades involve the gold lease rate. When lease rates are positive, you can earn by lending gold. This is different from typical currency carry trades.

### Volatility Trading

Gold volatility has specific characteristics. It tends to spike during risk-off events. Options strategies can capitalize on this behavior.

## Conclusion

Understanding gold markets requires knowledge of multiple factors. Supply and demand fundamentals matter, but macro drivers often dominate short-term price action.
"""

print("Testing MarkdownChunker")
print("=" * 80)
print(f"Input content: {len(test_content)} characters")
print()

# Create chunker
chunker = MarkdownChunker(
    target_chunk_size=150,  # Smaller for test visibility
    max_chunk_size=300,
    min_chunk_size=50
)

# Chunk the content
chunks = chunker.chunk_markdown(test_content)

print(f"✓ Created {len(chunks)} chunks")
print()

# Display each chunk
for i, chunk in enumerate(chunks):
    print(f"{'='*80}")
    print(f"Chunk {i}:")
    print(f"  Header Context: {chunk.header_context or '(no header)'}")
    print(f"  Token Count: {chunk.token_count}")
    print(f"  Content Length: {len(chunk.content)} chars")
    print(f"\nContent:")
    print(f"{chunk.content[:200]}...")
    print()

# Statistics
token_counts = [c.token_count for c in chunks]
print("=" * 80)
print("STATISTICS:")
print(f"  Total chunks: {len(chunks)}")
print(f"  Avg tokens: {sum(token_counts) / len(token_counts):.1f}")
print(f"  Min tokens: {min(token_counts)}")
print(f"  Max tokens: {max(token_counts)}")
print(f"  Total tokens: {sum(token_counts)}")

# Validation
print()
print("VALIDATION:")
oversized = [c for c in chunks if c.token_count > 300]
if oversized:
    print(f"  ✗ {len(oversized)} chunks exceed max size (300)!")
    for c in oversized:
        print(f"    - {c.token_count} tokens in '{c.header_context}'")
else:
    print(f"  ✓ All chunks within max size")

undersized = [c for c in chunks if c.token_count < 50]
if undersized:
    print(f"  ⚠ {len(undersized)} chunks below min size (50)")
else:
    print(f"  ✓ All chunks above min size")

# Check header preservation
print()
print("HEADER HIERARCHY CHECK:")
unique_headers = set(c.header_context for c in chunks if c.header_context)
print(f"  Found {len(unique_headers)} unique header contexts:")
for header in sorted(unique_headers):
    count = len([c for c in chunks if c.header_context == header])
    print(f"    - {header} ({count} chunks)")
