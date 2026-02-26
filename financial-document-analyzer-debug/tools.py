## Importing libraries and files
import os
from dotenv import load_dotenv
load_dotenv()

from crewai_tools import SerperDevTool
from crewai.tools import tool
from langchain_community.document_loaders import PyPDFLoader

## Creating search tool
search_tool = SerperDevTool()

## Creating custom pdf reader tool
class FinancialDocumentTool():
    @staticmethod
    @tool("Finalcial Document Reader")
    def read_data_tool(path : str ='data/TSLA-Q2-2025-Update.pdf') -> str:
        """Tool to read data from a pdf file from a path

        Args:
            path (str, optional): Path of the pdf file. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full Financial Document file
        """
        try:
            loader = PyPDFLoader(file_path=path)
            docs = loader.load()
            full_report = ""
        
            for data in docs:
              # Clean and format the financial document data
              content = data.page_content
            
              # Remove extra whitespaces and format properly
              while "\n\n" in content:
                 content = content.replace("\n\n", "\n")
                
              full_report += content + "\n"
            
            return full_report
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
        
## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    @tool("Investment Analyzer")
    def analyze_investment_tool(financial_document_data: str) -> str:
        """Analyzes financial document data and structures it for investment analysis.
        Args:
            financial_document_data (str): Raw financial document text content.
        Returns:
            str: Structured investment analysis prompt with key financial metrics.
        """

        if not financial_document_data:
            return "No financial data provided"
        # Process and analyze the financial document data
        processed_data = financial_document_data
        
        # Clean up the data format
        i = 0
        while i < len(processed_data):
            if processed_data[i:i+2] == "  ":  # Remove double spaces
                processed_data = processed_data[:i] + processed_data[i+1:]
            else:
                i += 1
                
    
        # structure the output for the agent
        analysis_prompt = f"""
            From the following financial document data, extract:
            1. Revenue and profit figures
            2. Year-over-year growth rates
            3. Key business segments performance
            4. Management guidance and outlook
            5. Potential investment opportunities and red flags

            Financial Data:
            {processed_data}
        """
        return analysis_prompt

## Creating Risk Assessment Tool
class RiskTool:

    @staticmethod
    @tool("Risk Assessor")
    def create_risk_assessment_tool(financial_document_data: str) -> str: 
        """Extracts risk-related sections from financial document data for risk assessment.
        Args:
            financial_document_data (str): Raw financial document text content.
        Returns:
            str: Structured risk assessment prompt with identified risk factors.
        """ 

        if not financial_document_data:
            return "No financial data provided for risk assessment"

        #Extract risk-related keywords and sections
        risk_keywords = [
            "risk", "uncertainty", "decline", "loss", "debt",
            "liability", "lawsuit", "competition", "regulation",
            "inflation", "interest rate", "default", "warning"
        ]    

        lines = financial_document_data.split("\n")
        risk_relevant_lines = []

        for line in lines:
            line_lower = line.lower()  
            if any(keyword in line_lower for keyword in risk_keywords):
                risk_relevant_lines.append(line.strip())

        if not risk_relevant_lines:
            risk_section = "No explicit risk factors found in document"
        else:
            risk_section = "\n".join(risk_relevant_lines)            

        # Structure output for the risk assessor agent
        risk_prompt = f"""
        Based on the following financial document data, assess:
        1. Market risks (competition, demand shifts)
        2. Financial risks (debt levels, liquidity, cash flow)
        3. Operational risks (supply chain, costs)
        4. Regulatory and legal risks
        5. Overall risk rating: Low / Medium / High

            Risk-relevant sections found:
            {risk_section}

            Full document context:
            {financial_document_data[:2000]}
        """
        return risk_prompt