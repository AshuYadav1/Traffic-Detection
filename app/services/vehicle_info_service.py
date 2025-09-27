"""
Vehicle Information Service
Fetches vehicle details from Parivahan or returns mock data
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
import asyncio
import aiohttp

class VehicleInfoService:
    def __init__(self):
        # Vehicle registration database
        self.mock_db = {
            "MH12DE1433": {
                "Registration No": "MH12DE1433",
                "Owner Name": "Ramesh Kumar",
                "Vehicle Class": "LMV",
                "Fuel Type": "Petrol",
                "Registration Date": "12-Jan-2016",
                "Chassis No": "MA1EZ12345",
                "Engine No": "EN98765PQ",
            },
            "DL8CAF5031": {
                "Registration No": "DL8CAF5031",
                "Owner Name": "Anita Sharma",
                "Vehicle Class": "SUV",
                "Fuel Type": "Diesel",
                "Registration Date": "05-Aug-2018",
                "Chassis No": "DLCH987654",
                "Engine No": "ENGD123456",
            },
            "KA01AB1111": {
                "Registration No": "KA01AB1111",
                "Owner Name": "Suresh Iyer",
                "Vehicle Class": "Motorcycle",
                "Fuel Type": "Petrol",
                "Registration Date": "22-Nov-2020",
                "Chassis No": "KA99887766",
                "Engine No": "MCENG445566",
            },
            "1206SHL": {
                "Registration No": "1206SHL",
                "Owner Name": "Rohan Mehra",
                "Vehicle Class": "Hatchback",
                "Fuel Type": "Diesel",
                "Registration Date": "14-Feb-2021",
                "Chassis No": "MH47XZ11223344556",
                "Engine No": "ENGT9F334455",
                "Image": "https://i.postimg.cc/63YSRCFZ/download.jpg"
            },
        }

    async def get_vehicle_info(self, first_part: str, second_part: str) -> Dict:
        """
        Get vehicle information from registration number
        """
        reg_no = first_part + second_part
        
        # Check mock database first
        if reg_no in self.mock_db:
            return self.mock_db[reg_no]
        
        # Try scraping from Parivahan
        try:
            vehicle_data = await self._scrape_parivahan(first_part, second_part)
            if vehicle_data and len(vehicle_data) > 0:
                return vehicle_data
        except Exception as e:
            print(f"Error scraping Parivahan: {e}")
        
        # Return error if not found
        return {"error": "Vehicle registration not found in database"}

    async def _scrape_parivahan(self, first_part: str, second_part: str) -> Optional[Dict]:
        """
        Scrape vehicle details from Parivahan website
        """
        try:
            async with aiohttp.ClientSession() as session:
                # First request to get session token
                async with session.post(
                    "https://parivahan.gov.in/rcdlstatus/",
                    data=None
                ) as first_resp:
                    html_content = await first_resp.text()
                    
                    # Parse HTML to get ViewState token
                    soup = BeautifulSoup(html_content, 'html.parser')
                    view_state_input = soup.find('input', {'name': 'javax.faces.ViewState'})
                    token = view_state_input['value'] if view_state_input else ""
                    
                    # Get cookies
                    cookies = {}
                    for cookie in first_resp.cookies:
                        cookies[cookie.key] = cookie.value

                # Prepare form data
                form_data = {
                    "javax.faces.partial.ajax": "true",
                    "javax.faces.source": "form_rcdl:j_idt32",
                    "javax.faces.partial.execute": "@all",
                    "javax.faces.partial.render": "form_rcdl:pnl_show form_rcdl:pg_show form_rcdl:rcdl_pnl",
                    "form_rcdl:j_idt32": "form_rcdl:j_idt32",
                    "form_rcdl": "form_rcdl",
                    "form_rcdl:tf_reg_no1": first_part,
                    "form_rcdl:tf_reg_no2": second_part,
                    "javax.faces.ViewState": token
                }

                # Second request with form data
                async with session.post(
                    "https://parivahan.gov.in/rcdlstatus/",
                    data=form_data,
                    cookies=cookies,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                ) as second_resp:
                    html_content = await second_resp.text()
                    
                    # Parse vehicle details
                    soup = BeautifulSoup(html_content, 'html.parser')
                    response = {}
                    
                    # Find table and extract data
                    tables = soup.find_all('table')
                    for table in tables:
                        tds = table.find_all('td')
                        for i, td in enumerate(tds):
                            if td.find(class_='font-bold'):
                                key = td.find(class_='font-bold').get_text().strip()
                                if i + 1 < len(tds):
                                    next_td = tds[i + 1]
                                    value_elem = next_td.find(class_='font-bold')
                                    if value_elem and not value_elem.get_text().strip():
                                        continue
                                    value = next_td.get_text().strip() if not value_elem else value_elem.get_text().strip()
                                    if key and value:
                                        response[key] = value
                    
                    return response if response else None

        except Exception as e:
            print(f"Scraping error: {e}")
            return None

# Create global instance
vehicle_service = VehicleInfoService()
