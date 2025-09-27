import os
from datetime import timedelta

class Config:
    """Configuration class for Aviation Weather System"""
    
    # AI Configuration
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Weather Data Sources
    AVIATION_WEATHER_API = 'https://aviationweather.gov/api/data/'
    NOAA_METAR_BASE = 'https://tgftp.nws.noaa.gov/data/observations/metar/stations/'
    
    # Safety Configuration
    MAX_ANALYSIS_TIMEOUT = 30  # seconds
    FALLBACK_ANALYSIS_ENABLED = True
    LOG_LEVEL = 'INFO'
    
    # Rate Limiting
    MAX_REQUESTS_PER_MINUTE = 60
    
    # Cache Configuration
    CACHE_TIMEOUT = timedelta(minutes=10)  # Weather data cache
    
    # Airport Database
    MAJOR_AIRPORTS = {
        'KLAX': {'name': 'Los Angeles International Airport', 'city': 'Los Angeles', 'lat': 33.9425, 'lon': -118.4081},
        'KJFK': {'name': 'John F. Kennedy International Airport', 'city': 'New York', 'lat': 40.6398, 'lon': -73.7789},
        'KORD': {'name': 'O\'Hare International Airport', 'city': 'Chicago', 'lat': 41.9786, 'lon': -87.9047},
        'KDEN': {'name': 'Denver International Airport', 'city': 'Denver', 'lat': 39.8561, 'lon': -104.6737},
        'KSFO': {'name': 'San Francisco International Airport', 'city': 'San Francisco', 'lat': 37.6190, 'lon': -122.3748},
        
        # Indian Airports
        'VOBL': {'name': 'Kempegowda International Airport', 'city': 'Bangalore', 'lat': 12.9716, 'lon': 77.5946},
        'VIDP': {'name': 'Indira Gandhi International Airport', 'city': 'Delhi', 'lat': 28.5562, 'lon': 77.1000},
        'VABB': {'name': 'Chhatrapati Shivaji International Airport', 'city': 'Mumbai', 'lat': 19.0896, 'lon': 72.8656},
        'VECC': {'name': 'Netaji Subhas Chandra Bose International Airport', 'city': 'Kolkata', 'lat': 22.6547, 'lon': 88.4467},
        'VOMM': {'name': 'Chennai International Airport', 'city': 'Chennai', 'lat': 13.0827, 'lon': 80.2707},
    }
    
    # Common flight routes
    COMMON_ROUTES = [
        ['KLAX', 'KJFK'],  # LA to New York
        ['KLAX', 'KORD'],  # LA to Chicago
        ['KJFK', 'KSFO'],  # New York to San Francisco
        ['VOBL', 'VIDP'],  # Bangalore to Delhi
        ['VOBL', 'VABB'],  # Bangalore to Mumbai
        ['VIDP', 'VABB'],  # Delhi to Mumbai
    ]
    
    @classmethod
    def get_airport_info(cls, icao: str) -> dict:
        """Get airport info from predefined list or return default"""
        icao = icao.upper()
        return cls.MAJOR_AIRPORTS.get(icao, {
            'name': f'Airport {icao}',
            'city': 'Unknown',
            'lat': None,
            'lon': None
        })