from sqlalchemy import text

def get_open_positions(engine, limit=100):
    # Список всех открытых позиций — для команды /positions
    sql = text("""
        SELECT id, symbol,
               notional_usdt,
               spot_entry_price, fut_entry_price,
               price_pnl_usdt,
               funding_pnl_usdt,
               fees_paid_usdt,
               total_pnl_usdt,
               opened_at
        FROM paper_positions
        WHERE status = 'OPEN'
        ORDER BY opened_at DESC
        LIMIT :limit
    """)
    
    with engine.connect() as conn:

        return conn.execute(sql, {'limit': limit}).mappings().all()

def get_total_pnl_summary(engine):
    # Агрегированный PnL — для команды /pnl
    sql = text("""
        SELECT 
            COUNT(*)                    as open_positions,
            SUM(notional_usdt)          as total_notional,
            SUM(price_pnl_usdt)         as total_price_pnl,
            SUM(funding_pnl_usdt)       as total_funding_pnl,
            SUM(fees_paid_usdt)         as total_fees,
            SUM(total_pnl_usdt)         as total_pnl
        FROM paper_positions
        WHERE status = 'OPEN'
    """)

    with engine.connect() as conn:

        return conn.execute(sql).mappings().first()

def get_cashflow_history(engine, symbol, limit=10):
    # Последние N funding выплат по символу — для детализации
    sql = text("""
        SELECT pfc.funding_time,
               pfc.funding_rate,
               pfc.mark_price,
               pfc.notional_usdt,
               pfc.cashflow_usdt,
               SUM(pfc.cashflow_usdt) OVER (
                   PARTITION BY pfc.position_id
                   ORDER BY pfc.funding_time
               ) as cumulative_cashflow
        FROM paper_funding_cashflows pfc
        JOIN paper_positions pp ON pp.id = pfc.position_id
        WHERE pp.symbol = :symbol
        AND pp.status = 'OPEN'
        ORDER BY pfc.funding_time DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:

        return conn.execute(sql, {'symbol': symbol, "limit": limit}).mappings().first()

def get_positions_pnl_alert(engine, threshold_pct=0.02):
    # Позиции где total_pnl превысил порог от notional — для алерта
    sql = text("""
        SELECT symbol,
               total_pnl_usdt,
               notional_usdt,
               total_pnl_usdt / notional_usdt as pnl_pct
        FROM paper_positions
        WHERE status = 'OPEN'
        AND ABS(total_pnl_usdt / notional_usdt) >= :threshold
        ORDER BY pnl_pct DESC
    """)

    with engine.connect() as conn:

        return conn.execute(sql, {'threshold': threshold_pct}).mappings().all()
