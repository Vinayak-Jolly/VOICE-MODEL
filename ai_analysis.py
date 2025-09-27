# ai_analysis.py - GenAI Integration for Weather Analysis (DeepSeek primary, Gemini fallback)

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DEEPSEEK_BASE = "https://api.deepseek.com"   # OpenAI-compatible base
DEEPSEEK_MODEL = "deepseek-chat"             # concise chat model

class WeatherAIAnalyst:
    def __init__(self):
        # Primary: DeepSeek
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        # Fallback: Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Initialize API clients
        self.deepseek_client = None
        self.gemini_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize API clients with error handling"""
        # DeepSeek client
        if self.deepseek_api_key:
            try:
                from openai import OpenAI
                self.deepseek_client = OpenAI(
                    api_key=self.deepseek_api_key, 
                    base_url=DEEPSEEK_BASE
                )
                logger.info("DeepSeek client initialized successfully")
            except ImportError:
                logger.warning("OpenAI package not available for DeepSeek")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek client: {e}")

        # Gemini client
        if self.gemini_api_key:
            try:
                # Try new SDK first
                try:
                    from google import genai
                    self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                    self.gemini_sdk_version = "new"
                    logger.info("Gemini client (new SDK) initialized successfully")
                except ImportError:
                    # Fallback to old SDK
                    import google.generativeai as genai_old
                    genai_old.configure(api_key=self.gemini_api_key)
                    self.gemini_client = genai_old
                    self.gemini_sdk_version = "old"
                    logger.info("Gemini client (old SDK) initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

    # ---------------- public API ----------------
    def generate_pilot_briefing(self, weather_data: Dict[str, Any], route_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive pilot briefing using AI"""
        try:
            context = self._prepare_weather_context(weather_data, route_info)
            return {
                'executive_summary': self._generate_executive_summary(context),
                'detailed_analysis': self._generate_detailed_analysis(context),
                'operational_impact': self._generate_operational_impact(context),
                'altitude_specific': self._generate_altitude_analysis(context),
                'timing_considerations': self._generate_timing_analysis(context),
                'risk_assessment': self._generate_risk_assessment(context),
                'recommendations': self._generate_recommendations(context),
                'plain_english': self._generate_plain_english_summary(context),
            }
        except Exception as e:
            logger.error(f"Failed to generate pilot briefing: {e}")
            return self._get_fallback_briefing()

    def _get_fallback_briefing(self) -> Dict[str, Any]:
        """Return fallback briefing when AI services fail"""
        return {
            'executive_summary': 'AI analysis temporarily unavailable. Please review raw weather data.',
            'detailed_analysis': 'Manual weather analysis required at this time.',
            'operational_impact': 'Refer to official weather sources for operational decisions.',
            'altitude_specific': {'Surface-3000ft': 'Analysis unavailable', '3000-10000ft': 'Analysis unavailable', '10000-18000ft': 'Analysis unavailable', '18000ft+': 'Analysis unavailable'},
            'timing_considerations': 'Check latest METAR and TAF updates.',
            'risk_assessment': {'overall_risk_level': 'UNKNOWN', 'primary_risks': ['AI service unavailable'], 'secondary_risks': [], 'mitigation_strategies': ['Manual analysis required'], 'confidence_level': 'LOW', 'monitoring_points': ['Weather updates']},
            'recommendations': ['Monitor official weather sources', 'Consult with flight dispatch', 'Review NOTAMs and SIGMETs'],
            'plain_english': 'Weather analysis is currently being updated. Please check back shortly.'
        }

    # ---------------- context builder ----------------
    def _prepare_weather_context(self, weather_data: Dict, route_info: Dict) -> str:
        """Prepare structured context for AI analysis"""
        parts = []

        # Route info
        if route_info.get('airports'):
            airports = [a['code'] for a in route_info['airports']]
            parts.append(f"ROUTE: {' -> '.join(airports)}")

        # Weather per airport
        for airport in route_info.get('airports', []):
            code = airport['code']
            current = airport.get('current_weather', {})
            if current.get('raw_text'):
                parts.append(f"METAR {code}: {current['raw_text']}")
            
            # Add parsed weather details if available
            if current.get('parsed'):
                parsed = current['parsed']
                if parsed.get('wind'):
                    wind = parsed['wind']
                    parts.append(f"Wind {code}: {wind.get('direction', 'VRB')}° at {wind.get('speed', 0)} kt")
                if parsed.get('visibility'):
                    vis = parsed['visibility']
                    parts.append(f"Visibility {code}: {vis.get('value', 'Unknown')} {vis.get('unit', '')}")
                if parsed.get('weather'):
                    wx = [w.get('name', '') for w in parsed['weather']]
                    if wx:
                        parts.append(f"Weather {code}: {', '.join(wx)}")

        # Overall notes
        if route_info.get('overall_conditions'):
            parts.append(f"OVERALL CONDITIONS: {route_info['overall_conditions']}")

        return "\n".join(parts)

    # ---------------- section generators ----------------
    def _generate_executive_summary(self, context: str) -> str:
        prompt = f"""
You are an experienced flight dispatcher and meteorologist. Based on the following weather data, provide a concise executive summary for pilots in 2-3 sentences:

{context}

Focus on:
- Overall flight conditions (GO/NO-GO/MONITOR)
- Most significant weather threats
- Key decision points

Write in professional aviation terminology but keep it concise and actionable.
"""
        return self._call_ai_service(prompt, max_tokens=150)

    def _generate_detailed_analysis(self, context: str) -> str:
        prompt = f"""
You are a certified meteorologist providing detailed weather analysis for aviation operations. Based on the following weather data:

{context}

Structure your analysis to cover:
1. Current conditions at each airport
2. Forecast trends and timing
3. Weather phenomena and their aviation impacts
4. Visibility and ceiling considerations
5. Wind patterns and potential turbulence
6. Precipitation and icing threats

Use technical meteorological terms but explain their operational significance.
"""
        return self._call_ai_service(prompt, max_tokens=600)

    def _generate_operational_impact(self, context: str) -> str:
        prompt = f"""
You are an airline operations manager assessing the operational impact of weather conditions. Based on:

{context}

Address:
- Potential delays and their causes
- Fuel planning considerations
- Alternate airport requirements
- Crew duty time impacts
- Passenger service implications
- Aircraft performance factors

Provide specific, actionable insights for flight operations.
"""
        return self._call_ai_service(prompt, max_tokens=400)

    def _generate_altitude_analysis(self, context: str) -> Dict[str, str]:
        """Returns {band: text} for four altitude bands."""
        bands = ['Surface-3000ft', '3000-10000ft', '10000-18000ft', '18000ft+']
        out: Dict[str, str] = {}
        for band in bands:
            prompt = f"""
For {band} altitude band based on this weather data:

{context}

Analyze:
- Wind conditions and shear potential
- Temperature and icing conditions
- Turbulence potential
- Visibility restrictions
- Cloud layers and precipitation

Keep the analysis specific to this altitude band.
"""
            out[band] = self._call_ai_service(prompt, max_tokens=250)
        return out

    def _generate_timing_analysis(self, context: str) -> str:
        prompt = f"""
You are a flight planning specialist analyzing weather timing. Based on:

{context}

Analyze:
- Optimal departure windows
- Weather improvement/deterioration trends
- Critical timing for weather changes
- Forecast confidence levels

Provide specific timing recommendations.
"""
        return self._call_ai_service(prompt, max_tokens=300)

    def _generate_risk_assessment(self, context: str) -> Dict[str, Any]:
        prompt = f"""
Based on this weather data:

{context}

Provide risk assessment in JSON format with these exact keys:
- overall_risk_level: (LOW/MODERATE/HIGH/SEVERE)
- primary_risks: [list of main weather risks]
- secondary_risks: [list of secondary concerns]
- mitigation_strategies: [list of risk mitigation actions]
- confidence_level: (HIGH/MEDIUM/LOW)
- monitoring_points: [list of conditions to monitor]

Return only valid JSON, no other text.
"""
        response = self._call_ai_service(prompt, max_tokens=300)
        try:
            # Clean the response to extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI risk assessment: {e}")
            return {
                'overall_risk_level': 'MODERATE',
                'primary_risks': ['Unable to parse AI assessment'],
                'secondary_risks': ['Manual analysis required'],
                'mitigation_strategies': ['Consult official weather sources'],
                'confidence_level': 'LOW',
                'monitoring_points': ['Weather updates'],
            }

    def _generate_recommendations(self, context: str) -> List[str]:
        prompt = f"""
You are an experienced chief pilot providing operational recommendations. Based on:

{context}

Provide specific, actionable recommendations as a bullet list covering:
- Go/No-go decision factors
- Fuel planning adjustments
- Route modifications
- Altitude considerations
- Equipment requirements

Format as simple bullet points, be specific and actionable.
"""
        response = self._call_ai_service(prompt, max_tokens=300)
        recs: List[str] = []
        for line in response.splitlines():
            line = line.strip()
            if not line:
                continue
            # Extract bullet points or numbered items
            if line.startswith(('•', '-', '*', '1.', '2.', '3.')):
                clean_line = line.lstrip('•-* 1234567890.').strip()
                if clean_line and len(clean_line) > 10:  # Meaningful content
                    recs.append(clean_line)
            elif len(line) > 20 and not line.startswith(('Based on', 'Recommendation')):  # Standalone lines
                recs.append(line)
        return recs[:6] if recs else ['Monitor weather conditions', 'Review flight planning', 'Consult with dispatch']

    def _generate_plain_english_summary(self, context: str) -> str:
        prompt = f"""
Explain this aviation weather data to passengers and non-technical staff:

{context}

Write in simple terms that anyone can understand:
- What the weather is like now
- What to expect during the flight
- Any potential impacts on comfort or timing
- Overall outlook (good/challenging/concerning)

Avoid technical jargon and focus on passenger-relevant information.
"""
        return self._call_ai_service(prompt, max_tokens=200)

    # ---------------- provider selection ----------------
    def _call_ai_service(self, prompt: str, max_tokens: int = 500) -> str:
        # Try DeepSeek first
        if self.deepseek_client:
            try:
                result = self._call_deepseek(prompt, max_tokens)
                if result:
                    logger.info("AI provider: DeepSeek")
                    return result
            except Exception as e:
                logger.warning(f"DeepSeek call failed: {e}")

        # Fallback: Gemini
        if self.gemini_client:
            try:
                result = self._call_gemini(prompt, max_tokens)
                if result:
                    logger.info("AI provider: Gemini")
                    return result
            except Exception as e:
                logger.warning(f"Gemini call failed: {e}")

        # Final fallback
        return "AI analysis temporarily unavailable. Please refer to official weather sources."

    # ---------------- DeepSeek (primary) ----------------
    def _call_deepseek(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Calls DeepSeek via OpenAI-compatible SDK."""
        try:
            resp = self.deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert aviation meteorologist. Provide concise, accurate analysis."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return None

    # ---------------- Gemini (fallback) ----------------
    def _call_gemini(self, prompt: str, max_tokens: int) -> Optional[str]:
        """Calls Gemini API."""
        try:
            if self.gemini_sdk_version == "new":
                resp = self.gemini_client.models.generate_content(
                    model="gemini-2.0-flash-thinking-exp",
                    contents=prompt,
                    config={"max_output_tokens": max_tokens, "temperature": 0.2},
                )
                return resp.text.strip() if hasattr(resp, 'text') else None
            else:
                # Old SDK
                model = self.gemini_client.GenerativeModel("gemini-pro")
                resp = model.generate_content(
                    prompt,
                    generation_config={"max_output_tokens": max_tokens, "temperature": 0.2}
                )
                return resp.text.strip() if hasattr(resp, 'text') else None
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None


class WeatherInsightGenerator:
    """Generate additional weather insights and predictions"""

    def __init__(self, ai_analyst: WeatherAIAnalyst):
        self.ai_analyst = ai_analyst

    def generate_trend_analysis(self, historical_data: List[Dict], current_data: Dict) -> Dict[str, Any]:
        """Generate trend analysis based on historical and current data"""
        try:
            context = f"Historical trends: {len(historical_data)} data points. Current: {current_data}"
            prompt = f"""
            Analyze weather trends based on historical data and current conditions:
            {context}
            
            Provide trend analysis with:
            - trend_direction: improving/deteriorating/stable
            - confidence: high/medium/low
            - expected_changes: list of expected changes
            - time_to_change: estimated timeframe
            
            Return as JSON.
            """
            response = self.ai_analyst._call_ai_service(prompt, 300)
            try:
                return json.loads(response)
            except:
                return self._get_default_trend_analysis()
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return self._get_default_trend_analysis()

    def _get_default_trend_analysis(self) -> Dict[str, Any]:
        return {
            'trend_direction': 'stable',
            'confidence': 'medium',
            'expected_changes': ['No significant changes expected'],
            'time_to_change': 'Next 2-4 hours'
        }

    def generate_alternative_routes(self, primary_route: List[str], weather_data: Dict) -> List[Dict]:
        """Generate alternative routing options"""
        try:
            context = f"Primary route: {' -> '.join(primary_route)}. Weather: {weather_data}"
            prompt = f"""
            Suggest alternative flight routes considering weather conditions:
            {context}
            
            Provide 1-2 alternative routes with:
            - route: airport codes
            - weather_score: 1-10 rating
            - estimated_time: hours/minutes
            - fuel_impact: percentage change
            - reason: brief explanation
            
            Return as JSON list.
            """
            response = self.ai_analyst._call_ai_service(prompt, 400)
            try:
                return json.loads(response)
            except:
                return self._get_default_alternatives(primary_route)
        except Exception as e:
            logger.error(f"Alternative routes failed: {e}")
            return self._get_default_alternatives(primary_route)

    def _get_default_alternatives(self, primary_route: List[str]) -> List[Dict]:
        if len(primary_route) >= 2:
            return [{
                'route': primary_route,
                'weather_score': 7.5,
                'estimated_time': 'Similar to primary',
                'fuel_impact': '±5%',
                'reason': 'Standard routing with weather monitoring'
            }]
        return []

    def generate_weather_alerts(self, route_analysis: Dict) -> List[Dict[str, Any]]:
        """Generate weather alerts from route analysis"""
        alerts = []
        
        for airport in route_analysis.get('airports', []):
            severity = airport.get('current_weather', {}).get('parsed', {}).get('severity', 'UNKNOWN')
            code = airport.get('code', 'UNKNOWN')
            
            if severity == 'SEVERE':
                alerts.append({
                    'type': 'WARNING',
                    'location': code,
                    'message': f"Severe weather conditions at {code}",
                    'impact': 'High',
                    'action_required': 'Consider alternate airport'
                })
            elif severity == 'MODERATE':
                alerts.append({
                    'type': 'ADVISORY',
                    'location': code,
                    'message': f"Moderate weather impacts at {code}",
                    'impact': 'Medium',
                    'action_required': 'Enhanced monitoring recommended'
                })
        
        return alerts