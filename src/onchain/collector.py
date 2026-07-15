# ============================================================
#  ON-CHAIN COLLECTOR - Store on-chain data in database
#  With rate limiting to avoid 429 errors
# ============================================================

import time
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.core.logger import logger
from src.core.database import get_db
from src.models import OnChainData
from src.onchain.client import OnChainClient
from src.onchain.metrics import OnChainMetrics


class OnChainCollector:
    """Collect and store on-chain data with rate limiting."""
    
    def __init__(self):
        self.client = OnChainClient()
        self.metrics = OnChainMetrics()
        self.request_delay = 2.0  # 2 seconds between requests to avoid 429
    
    def collect_onchain_data(self, symbol: str) -> bool:
        """Collect on-chain data for a symbol and store in database."""
        try:
            # Rate limit delay
            time.sleep(self.request_delay)
            
            # Get on-chain metrics
            result = self.metrics.calculate_onchain_score(symbol)
            
            if not result:
                return False
            
            with get_db() as db:
                onchain_data = OnChainData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    score=result.get('score', 0),
                    direction=result.get('direction', 'NEUTRAL'),
                    confidence=result.get('confidence', 'LOW'),
                    whale_score=result.get('details', {}).get('whale', {}).get('score', 0),
                    whale_direction=result.get('details', {}).get('whale', {}).get('direction', 'NEUTRAL'),
                    accumulation_score=result.get('details', {}).get('accumulation', {}).get('score', 0),
                    accumulation_direction=result.get('details', {}).get('accumulation', {}).get('direction', 'NEUTRAL'),
                    network_score=result.get('details', {}).get('network', {}).get('score', 0),
                    network_direction=result.get('details', {}).get('network', {}).get('direction', 'NEUTRAL'),
                    details=result.get('details', {}),
                )
                db.add(onchain_data)
                db.commit()
            
            logger.debug(f"✅ On-chain data stored for {symbol}")
            return True
            
        except Exception as e:
            logger.debug(f"On-chain data not available for {symbol}: {e}")
            return False
    
    def collect_multiple(self, symbols: List[str]) -> Dict[str, int]:
        """Collect on-chain data for multiple symbols with rate limiting."""
        results = {'success': 0, 'failed': 0}
        
        # Only process top 10 coins to avoid rate limiting
        target_symbols = symbols[:10]
        logger.info(f"🔗 Collecting on-chain data for {len(target_symbols)} coins (rate-limited)")
        
        for symbol in target_symbols:
            if self.collect_onchain_data(symbol):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"📊 On-chain collection complete: {results['success']} success, {results['failed']} failed")
        return results