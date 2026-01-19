"""Model selection utility for ranking trading models.

Ports the model selection logic from PyTAAA to calculate which model
the meta-model should select at any given point in time.

The algorithm:
1. For each lookback period (e.g., 55, 157, 174 days)
2. Calculate performance metrics (annual return, Sharpe, Sortino, Calmar, max drawdown)
3. Normalize and rank models based on each metric
4. Compute weighted average rank across all metrics and lookback periods
5. Select the model with the best (lowest) average rank
"""
from typing import List, Dict, Tuple, Optional
from datetime import date as DateType, timedelta
import math
from collections import defaultdict


class ModelSelection:
    """Calculate model selection decisions based on historical performance."""
    
    # Metric weights (sum to 1.0)
    METRIC_WEIGHTS = {
        'annual_return': 0.25,
        'sharpe_ratio': 0.25,
        'max_drawdown': 0.20,
        'sortino_ratio': 0.15,
        'calmar_ratio': 0.15
    }
    
    # Default lookback periods (in trading days)
    DEFAULT_LOOKBACKS = [55, 157, 174]
    
    def __init__(self, lookback_periods: Optional[List[int]] = None):
        """Initialize model selection calculator.
        
        Args:
            lookback_periods: List of lookback periods in days (default: [55, 157, 174])
        """
        self.lookback_periods = lookback_periods or self.DEFAULT_LOOKBACKS
    
    def calculate_annual_return(self, values: List[float], days: int) -> float:
        """Calculate annualized return.
        
        Args:
            values: List of portfolio values (oldest to newest)
            days: Number of trading days
            
        Returns:
            Annualized return as decimal (0.15 = 15%)
        """
        if not values or len(values) < 2 or days <= 0:
            return 0.0
        
        start_value = values[0]
        end_value = values[-1]
        
        if start_value <= 0:
            return 0.0
        
        # Annualize assuming 252 trading days per year
        total_return = (end_value - start_value) / start_value
        years = days / 252.0
        
        if years <= 0:
            return 0.0
        
        annual_return = ((1 + total_return) ** (1 / years)) - 1
        return annual_return
    
    def calculate_returns(self, values: List[float]) -> List[float]:
        """Calculate daily returns from portfolio values.
        
        Args:
            values: List of portfolio values
            
        Returns:
            List of daily returns as decimals
        """
        if len(values) < 2:
            return []
        
        returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)
            else:
                returns.append(0.0)
        
        return returns
    
    def calculate_sharpe_ratio(self, values: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio.
        
        Args:
            values: List of portfolio values
            risk_free_rate: Annual risk-free rate (default 0.0)
            
        Returns:
            Sharpe ratio (annualized)
        """
        returns = self.calculate_returns(values)
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Annualize (252 trading days)
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        sharpe = ((mean_return - daily_rf) / std_dev) * math.sqrt(252)
        
        return sharpe
    
    def calculate_max_drawdown(self, values: List[float]) -> float:
        """Calculate maximum drawdown.
        
        Args:
            values: List of portfolio values
            
        Returns:
            Maximum drawdown as positive decimal (0.20 = 20% drawdown)
        """
        if not values:
            return 0.0
        
        max_value = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > max_value:
                max_value = value
            
            if max_value > 0:
                drawdown = (max_value - value) / max_value
                if drawdown > max_dd:
                    max_dd = drawdown
        
        return max_dd
    
    def calculate_sortino_ratio(self, values: List[float], risk_free_rate: float = 0.0) -> float:
        """Calculate Sortino ratio (like Sharpe but only penalizes downside volatility).
        
        Args:
            values: List of portfolio values
            risk_free_rate: Annual risk-free rate (default 0.0)
            
        Returns:
            Sortino ratio (annualized)
        """
        returns = self.calculate_returns(values)
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        daily_rf = (1 + risk_free_rate) ** (1/252) - 1
        
        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in returns if r < daily_rf]
        
        if not downside_returns:
            return 0.0  # No downside volatility
        
        downside_variance = sum((r - daily_rf) ** 2 for r in downside_returns) / len(returns)
        downside_dev = math.sqrt(downside_variance)
        
        if downside_dev == 0:
            return 0.0
        
        # Annualize
        sortino = ((mean_return - daily_rf) / downside_dev) * math.sqrt(252)
        
        return sortino
    
    def calculate_calmar_ratio(self, values: List[float], days: int) -> float:
        """Calculate Calmar ratio (annual return / max drawdown).
        
        Args:
            values: List of portfolio values
            days: Number of trading days
            
        Returns:
            Calmar ratio
        """
        annual_return = self.calculate_annual_return(values, days)
        max_dd = self.calculate_max_drawdown(values)
        
        if max_dd == 0:
            return 0.0
        
        return annual_return / max_dd
    
    def calculate_all_metrics(self, values: List[float], days: int) -> Dict[str, float]:
        """Calculate all performance metrics for a model.
        
        Args:
            values: List of portfolio values (oldest to newest)
            days: Number of trading days
            
        Returns:
            Dict with metric names and values
        """
        return {
            'annual_return': self.calculate_annual_return(values, days),
            'sharpe_ratio': self.calculate_sharpe_ratio(values),
            'max_drawdown': self.calculate_max_drawdown(values),
            'sortino_ratio': self.calculate_sortino_ratio(values),
            'calmar_ratio': self.calculate_calmar_ratio(values, days)
        }
    
    def rank_models(self, model_metrics: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Rank models based on their metrics.
        
        For each metric, assign ranks (1 = best, N = worst).
        Then compute weighted average rank.
        
        Args:
            model_metrics: Dict of {model_name: {metric_name: value}}
            
        Returns:
            Dict of {model_name: average_rank}
        """
        if not model_metrics:
            return {}
        
        model_names = list(model_metrics.keys())
        metric_names = list(self.METRIC_WEIGHTS.keys())
        
        # For each metric, rank the models
        metric_ranks = defaultdict(dict)
        
        for metric in metric_names:
            # Get metric values for all models
            metric_values = [(name, model_metrics[name].get(metric, 0.0)) 
                           for name in model_names]
            
            # Sort by value (higher is better for all except max_drawdown)
            if metric == 'max_drawdown':
                # Lower drawdown is better
                metric_values.sort(key=lambda x: x[1])
            else:
                # Higher is better
                metric_values.sort(key=lambda x: x[1], reverse=True)
            
            # Assign ranks (1 = best)
            for rank, (name, value) in enumerate(metric_values, start=1):
                metric_ranks[name][metric] = rank
        
        # Calculate weighted average rank for each model
        average_ranks = {}
        for name in model_names:
            weighted_sum = sum(
                metric_ranks[name][metric] * self.METRIC_WEIGHTS[metric]
                for metric in metric_names
            )
            average_ranks[name] = weighted_sum
        
        return average_ranks
    
    def select_best_model(
        self,
        backtest_data: Dict[str, List[Tuple[DateType, float]]],
        target_date: DateType
    ) -> Tuple[str, float, Dict[str, float]]:
        """Select the best model for a given date based on lookback analysis.
        
        Args:
            backtest_data: Dict of {model_name: [(date, traded_value), ...]}
            target_date: Date to make selection for
            
        Returns:
            Tuple of (best_model_name, confidence_score, model_ranks)
            confidence_score is the rank difference between 1st and 2nd place
        """
        # For each lookback period, calculate metrics for each model
        all_ranks = []
        
        for lookback_days in self.lookback_periods:
            cutoff_date = target_date - timedelta(days=lookback_days)
            
            model_metrics = {}
            
            for model_name, data_points in backtest_data.items():
                # Filter data points within lookback window
                filtered_points = [
                    (date, value) for date, value in data_points
                    if cutoff_date <= date <= target_date
                ]
                
                if not filtered_points or len(filtered_points) < 2:
                    # Not enough data for this lookback period
                    continue
                
                values = [value for _, value in filtered_points]
                actual_days = len(filtered_points)
                
                metrics = self.calculate_all_metrics(values, actual_days)
                model_metrics[model_name] = metrics
            
            if not model_metrics:
                continue
            
            # Rank models for this lookback period
            ranks = self.rank_models(model_metrics)
            all_ranks.append(ranks)
        
        if not all_ranks:
            # No data available
            return ('cash', 0.0, {})
        
        # Average ranks across all lookback periods
        final_ranks = defaultdict(float)
        for ranks in all_ranks:
            for model_name, rank in ranks.items():
                final_ranks[model_name] += rank
        
        # Average by number of lookback periods
        for model_name in final_ranks:
            final_ranks[model_name] /= len(all_ranks)
        
        # Select model with best (lowest) average rank
        if not final_ranks:
            return ('cash', 0.0, {})
        
        sorted_models = sorted(final_ranks.items(), key=lambda x: x[1])
        best_model = sorted_models[0][0]
        best_rank = sorted_models[0][1]
        
        # Calculate confidence (rank difference between 1st and 2nd)
        if len(sorted_models) > 1:
            second_rank = sorted_models[1][1]
            confidence = second_rank - best_rank
        else:
            confidence = 0.0
        
        return (best_model, confidence, dict(final_ranks))
