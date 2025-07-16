import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const App = () => {
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState(null);
  const [qaQuestion, setQaQuestion] = useState('');
  const [qaAnswer, setQaAnswer] = useState(null);
  const [summarizeLoading, setSummarizeLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeTab, setActiveTab] = useState('structure');
  const [relatedSections, setRelatedSections] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pdfData, setPdfData] = useState(null);
  const fileInputRef = useRef(null);
  const canvasRef = useRef(null);

  const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    if (selectedDocument) {
      loadPDFContent();
    }
  }, [selectedDocument]);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const loadPDFContent = async () => {
    if (!selectedDocument) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents/${selectedDocument.id}/pdf`);
      setPdfData(response.data.pdf_base64);
      setTotalPages(selectedDocument.total_pages);
      setCurrentPage(1);
      
      // Load PDF.js dynamically
      if (window.pdfjsLib) {
        renderPDF(response.data.pdf_base64);
      } else {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = () => {
          window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
          renderPDF(response.data.pdf_base64);
        };
        document.head.appendChild(script);
      }
    } catch (error) {
      console.error('Error loading PDF content:', error);
    }
  };

  const renderPDF = async (base64Data) => {
    try {
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      const pdf = await window.pdfjsLib.getDocument({data: bytes}).promise;
      const page = await pdf.getPage(currentPage);
      
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      const viewport = page.getViewport({scale: 1.5});
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      
      const renderContext = {
        canvasContext: context,
        viewport: viewport
      };
      
      await page.render(renderContext).promise;
    } catch (error) {
      console.error('Error rendering PDF:', error);
    }
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      if (pdfData) {
        renderPDF(pdfData);
      }
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/documents/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setDocuments([...documents, response.data]);
      setSelectedDocument(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error uploading document:', error);
      setLoading(false);
      alert('Error uploading document. Please try again.');
    }
  };

  const handleSearch = async () => {
    if (!selectedDocument || !searchQuery.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/documents/${selectedDocument.id}/search`, {
        document_id: selectedDocument.id,
        query: searchQuery,
        limit: 10
      });
      setSearchResults(response.data);
      setActiveTab('search');
    } catch (error) {
      console.error('Error searching document:', error);
    }
    setLoading(false);
  };

  const handleSectionClick = async (section) => {
    setActiveSection(section);
    
    // Load related sections
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents/${selectedDocument.id}/related/${section.id}`);
      setRelatedSections(response.data);
      
      // Navigate to section's page
      if (section.page_number && section.page_number !== currentPage) {
        setCurrentPage(section.page_number);
        if (pdfData) {
          renderPDF(pdfData);
        }
      }
    } catch (error) {
      console.error('Error loading related sections:', error);
    }
  };

  const handleSummarize = async (sectionId = null) => {
    if (!selectedDocument) return;

    setSummarizeLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/documents/${selectedDocument.id}/summarize`, {
        document_id: selectedDocument.id,
        section_id: sectionId,
        max_length: 5
      });
      
      alert(`Summary (${response.data.method}):\n\n${response.data.summary}`);
    } catch (error) {
      console.error('Error summarizing:', error);
      alert('Error generating summary. Please try again.');
    }
    setSummarizeLoading(false);
  };

  const handleQA = async () => {
    if (!selectedDocument || !qaQuestion.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/documents/${selectedDocument.id}/qa`, {
        document_id: selectedDocument.id,
        question: qaQuestion,
        context_limit: 3
      });
      setQaAnswer(response.data);
      setActiveTab('qa');
    } catch (error) {
      console.error('Error getting answer:', error);
    }
    setLoading(false);
  };

  const renderStructureTab = () => (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold mb-4">Document Structure</h3>
      {selectedDocument?.structure?.map((section) => (
        <div 
          key={section.id}
          className={`p-3 rounded-lg cursor-pointer transition-colors ${
            activeSection?.id === section.id ? 'bg-blue-100 border-l-4 border-blue-500' : 'bg-gray-50 hover:bg-gray-100'
          }`}
          style={{ marginLeft: `${(section.level - 1) * 20}px` }}
          onClick={() => handleSectionClick(section)}
        >
          <div className="flex items-center justify-between">
            <span className="font-medium text-sm">{section.title}</span>
            <span className="text-xs text-gray-500">Page {section.page_number}</span>
          </div>
          {activeSection?.id === section.id && (
            <div className="mt-2 text-xs text-gray-600">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleSummarize(section.id);
                }}
                className="text-blue-600 hover:underline mr-2"
                disabled={summarizeLoading}
              >
                {summarizeLoading ? 'Summarizing...' : 'Summarize'}
              </button>
              <span className="text-gray-400">•</span>
              <span className="ml-2">Level {section.level}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const renderSearchTab = () => (
    <div className="space-y-4">
      <div className="sticky top-0 bg-white pb-4 border-b">
        <div className="flex space-x-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search the document..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>
      
      <div className="space-y-3">
        {searchResults.map((result) => (
          <div key={result.section_id} className="bg-gray-50 p-3 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-sm">{result.title}</h4>
              <span className="text-xs text-gray-500">
                Page {result.page_number} • {(result.similarity_score * 100).toFixed(1)}% match
              </span>
            </div>
            <p className="text-sm text-gray-700 mb-2">{result.content}</p>
            {result.related_sections.length > 0 && (
              <div className="text-xs text-blue-600">
                Related: {result.related_sections.length} sections
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );

  const renderQATab = () => (
    <div className="space-y-4">
      <div className="sticky top-0 bg-white pb-4 border-b">
        <div className="flex space-x-2">
          <input
            type="text"
            value={qaQuestion}
            onChange={(e) => setQaQuestion(e.target.value)}
            placeholder="Ask a question about the document..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyPress={(e) => e.key === 'Enter' && handleQA()}
          />
          <button
            onClick={handleQA}
            disabled={loading}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            {loading ? 'Asking...' : 'Ask'}
          </button>
        </div>
      </div>
      
      {qaAnswer && (
        <div className="bg-green-50 p-4 rounded-lg">
          <h4 className="font-medium text-sm mb-2">Answer ({qaAnswer.method}):</h4>
          <p className="text-sm text-gray-700 mb-3">{qaAnswer.answer}</p>
          <div className="text-xs text-gray-500">
            Based on {qaAnswer.relevant_sections.length} relevant sections
          </div>
        </div>
      )}
    </div>
  );

  const renderRelatedTab = () => (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold mb-4">Related Sections</h3>
      {activeSection ? (
        <div className="space-y-3">
          <div className="bg-blue-50 p-3 rounded-lg">
            <h4 className="font-medium text-sm">Current Section:</h4>
            <p className="text-sm text-gray-700">{activeSection.title}</p>
          </div>
          {relatedSections.map((section) => (
            <div key={section.id} className="bg-gray-50 p-3 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-sm">{section.title}</h4>
                <span className="text-xs text-gray-500">Page {section.page_number}</span>
              </div>
              <p className="text-sm text-gray-700">{section.content}</p>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center text-gray-500 py-8">
          Select a section to see related content
        </div>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-bold text-gray-900">Offline PDF Reader</h1>
              <div className="text-sm text-green-600 bg-green-100 px-2 py-1 rounded">
                ✓ Works Without Internet
              </div>
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-md hover:bg-gray-100"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                disabled={loading}
              >
                {loading ? 'Processing...' : 'Upload PDF'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
              {selectedDocument && (
                <button
                  onClick={() => handleSummarize()}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                  disabled={summarizeLoading}
                >
                  {summarizeLoading ? 'Summarizing...' : 'Summarize Document'}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="flex h-screen">
        {/* Sidebar */}
        <div className={`bg-white shadow-lg transition-all duration-300 ${sidebarOpen ? 'w-96' : 'w-0'} overflow-hidden`}>
          <div className="p-4">
            {/* Document List */}
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-3">Documents</h2>
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedDocument?.id === doc.id ? 'bg-blue-100 border-l-4 border-blue-500' : 'bg-gray-50 hover:bg-gray-100'
                    }`}
                    onClick={() => setSelectedDocument(doc)}
                  >
                    <div className="font-medium text-sm truncate">{doc.title}</div>
                    <div className="text-xs text-gray-500">{doc.total_pages} pages</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Navigation Tabs */}
            {selectedDocument && (
              <div className="border-t pt-4">
                <div className="flex space-x-1 mb-4">
                  {[
                    { id: 'structure', label: 'Structure', icon: '📋' },
                    { id: 'search', label: 'Search', icon: '🔍' },
                    { id: 'qa', label: 'Q&A', icon: '❓' },
                    { id: 'related', label: 'Related', icon: '🔗' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex-1 px-3 py-2 text-xs font-medium rounded-md transition-colors ${
                        activeTab === tab.id
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <span className="mr-1">{tab.icon}</span>
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab Content */}
                <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
                  {activeTab === 'structure' && renderStructureTab()}
                  {activeTab === 'search' && renderSearchTab()}
                  {activeTab === 'qa' && renderQATab()}
                  {activeTab === 'related' && renderRelatedTab()}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 bg-white">
          {selectedDocument ? (
            <div className="h-full flex flex-col">
              {/* PDF Controls */}
              <div className="bg-gray-50 border-b p-4 flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <button
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage <= 1}
                    className="px-3 py-1 bg-gray-200 text-gray-700 rounded disabled:opacity-50"
                  >
                    ← Previous
                  </button>
                  <span className="text-sm">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    className="px-3 py-1 bg-gray-200 text-gray-700 rounded disabled:opacity-50"
                  >
                    Next →
                  </button>
                </div>
                <div className="text-sm text-gray-500">
                  {selectedDocument.title}
                </div>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-auto p-4 bg-gray-100">
                <div className="flex justify-center">
                  <canvas
                    ref={canvasRef}
                    className="border border-gray-300 shadow-lg bg-white"
                    style={{ maxWidth: '100%', height: 'auto' }}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No document selected</h3>
                <p className="text-gray-500 mb-4">Upload a PDF to get started with offline intelligent reading</p>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Upload PDF
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;