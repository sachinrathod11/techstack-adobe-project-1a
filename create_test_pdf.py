#!/usr/bin/env python3
"""
Create a test PDF for the hackathon solution
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os

def create_test_pdf():
    """Create a test PDF with structured content"""
    filename = "/app/input/test_document.pdf"
    
    # Create the PDF
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Page 1
    c.drawString(100, height - 100, "UNDERSTANDING ARTIFICIAL INTELLIGENCE")
    c.drawString(100, height - 150, "A Comprehensive Guide to AI Technologies")
    c.drawString(100, height - 200, "")
    c.drawString(100, height - 250, "1. Introduction")
    c.drawString(120, height - 280, "Artificial Intelligence (AI) is transforming our world.")
    c.drawString(120, height - 310, "This document provides a comprehensive overview of AI technologies.")
    c.drawString(120, height - 340, "We will explore the foundations, applications, and future of AI.")
    c.drawString(100, height - 400, "1.1 What is Artificial Intelligence?")
    c.drawString(120, height - 430, "AI refers to the simulation of human intelligence in machines.")
    c.drawString(120, height - 460, "These systems can perform tasks that typically require human intelligence.")
    c.drawString(100, height - 520, "1.1.1 Types of AI")
    c.drawString(120, height - 550, "There are several types of AI systems:")
    c.drawString(140, height - 580, "- Narrow AI: Designed for specific tasks")
    c.drawString(140, height - 610, "- General AI: Human-level intelligence")
    c.drawString(140, height - 640, "- Superintelligence: Beyond human capabilities")
    
    c.showPage()
    
    # Page 2
    c.drawString(100, height - 100, "2. Machine Learning Fundamentals")
    c.drawString(120, height - 130, "Machine learning is a subset of AI that focuses on algorithms.")
    c.drawString(120, height - 160, "These algorithms can learn and improve from experience.")
    c.drawString(100, height - 220, "2.1 Supervised Learning")
    c.drawString(120, height - 250, "Supervised learning uses labeled training data.")
    c.drawString(120, height - 280, "The algorithm learns to map inputs to outputs.")
    c.drawString(100, height - 340, "2.1.1 Classification")
    c.drawString(120, height - 370, "Classification predicts discrete categories or classes.")
    c.drawString(120, height - 400, "Examples include spam detection and image recognition.")
    c.drawString(100, height - 460, "2.1.2 Regression")
    c.drawString(120, height - 490, "Regression predicts continuous numerical values.")
    c.drawString(120, height - 520, "Examples include price prediction and sales forecasting.")
    c.drawString(100, height - 580, "2.2 Unsupervised Learning")
    c.drawString(120, height - 610, "Unsupervised learning finds patterns in unlabeled data.")
    c.drawString(120, height - 640, "Common techniques include clustering and association rules.")
    
    c.showPage()
    
    # Page 3
    c.drawString(100, height - 100, "3. Deep Learning and Neural Networks")
    c.drawString(120, height - 130, "Deep learning is a subset of machine learning.")
    c.drawString(120, height - 160, "It uses artificial neural networks with multiple layers.")
    c.drawString(100, height - 220, "3.1 Neural Network Architecture")
    c.drawString(120, height - 250, "Neural networks consist of interconnected nodes called neurons.")
    c.drawString(120, height - 280, "Each connection has a weight that determines influence.")
    c.drawString(100, height - 340, "3.1.1 Input Layer")
    c.drawString(120, height - 370, "The input layer receives raw data from the environment.")
    c.drawString(120, height - 400, "Each neuron represents a feature of the input data.")
    c.drawString(100, height - 460, "3.1.2 Hidden Layers")
    c.drawString(120, height - 490, "Hidden layers perform complex computations on the input.")
    c.drawString(120, height - 520, "Deep networks can have many hidden layers.")
    c.drawString(100, height - 580, "3.2 Training Process")
    c.drawString(120, height - 610, "Training involves adjusting weights to minimize errors.")
    c.drawString(120, height - 640, "This process is called backpropagation.")
    
    c.showPage()
    
    # Page 4
    c.drawString(100, height - 100, "CONCLUSION")
    c.drawString(120, height - 130, "Artificial Intelligence is a rapidly evolving field.")
    c.drawString(120, height - 160, "Understanding its foundations is crucial for future developments.")
    c.drawString(120, height - 190, "The potential applications are limitless.")
    c.drawString(100, height - 250, "REFERENCES")
    c.drawString(120, height - 280, "[1] Russell, S., & Norvig, P. (2020). Artificial Intelligence: A Modern Approach.")
    c.drawString(120, height - 310, "[2] Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning.")
    c.drawString(120, height - 340, "[3] Mitchell, T. (1997). Machine Learning.")
    
    c.save()
    print(f"Created test PDF: {filename}")

if __name__ == "__main__":
    create_test_pdf()