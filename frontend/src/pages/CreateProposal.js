import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, Sparkles, Upload, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import ClauseSelector from '@/components/ClauseSelector';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const CreateProposal = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [templates, setTemplates] = useState([]);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [formData, setFormData] = useState({
    client_name: '',
    project_description: '',
    budget_range: '',
    timeline: '',
    selected_clauses: [],
    additional_requirements: '',
    template_id: 'none',
    deal_value: ''
  });

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API}/templates`);
      setTemplates(response.data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleClausesChange = (selectedIds) => {
    setFormData({
      ...formData,
      selected_clauses: selectedIds
    });
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.pdf') && !file.name.endsWith('.txt')) {
      toast.error('Only PDF and TXT files are supported');
      return;
    }

    try {
      setUploading(true);
      const formDataObj = new FormData();
      formDataObj.append('file', file);

      const response = await axios.post(`${API}/upload-document`, formDataObj, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setUploadedFile({
        name: response.data.filename,
        content: response.data.content
      });
      toast.success('File uploaded successfully');
    } catch (error) {
      console.error('Error uploading file:', error);
      toast.error('Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateAndSave = async (e) => {
    e.preventDefault();

    if (!formData.client_name || !formData.project_description || !formData.budget_range || !formData.timeline) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setGenerating(true);
      
      const generatePayload = {
        ...formData,
        uploaded_file_content: uploadedFile?.content || null,
        deal_value: formData.deal_value ? parseFloat(formData.deal_value) : null
      };

      // AI generation can take time, so we increase the timeout to 120 seconds
      const generateResponse = await axios.post(`${API}/generate-proposal`, generatePayload, {
        timeout: 120000 // 120 seconds timeout for AI generation
      });
      const generatedContent = generateResponse.data.content;

      setLoading(true);
      
      const proposalData = {
        client_name: formData.client_name,
        project_description: formData.project_description,
        budget_range: formData.budget_range,
        timeline: formData.timeline,
        selected_clauses: formData.selected_clauses,
        content: generatedContent,
        status: 'Draft',
        deal_value: formData.deal_value ? parseFloat(formData.deal_value) : null
      };

      const createResponse = await axios.post(`${API}/proposals`, proposalData);
      
      toast.success('Proposal generated and saved successfully!');
      navigate(`/proposals/${createResponse.data.id}`);
    } catch (error) {
      console.error('Error creating proposal:', error);
      if (error.code === 'ECONNABORTED') {
        toast.error('AI generation timed out. Please try again with a shorter description.');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to generate proposal');
      }
    } finally {
      setGenerating(false);
      setLoading(false);
    }
  };

  return (
    <div className="p-8" data-testid="create-proposal-page">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard')}
            className="mb-4"
            data-testid="back-button"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
          <h1 className="font-outfit text-4xl font-semibold tracking-tight text-slate-900 mb-2">
            Create New Proposal
          </h1>
          <p className="text-slate-600">Fill in the details to generate an AI-powered proposal</p>
        </div>

        <form onSubmit={handleGenerateAndSave}>
          <Card className="border-slate-200 shadow-sm mb-6">
            <CardHeader>
              <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
                Template Selection (Optional)
              </CardTitle>
              <CardDescription>Choose an industry template to tailor your proposal</CardDescription>
            </CardHeader>
            <CardContent>
              <Select
                value={formData.template_id}
                onValueChange={(value) => setFormData({ ...formData, template_id: value })}
              >
                <SelectTrigger className="border-slate-200" data-testid="template-select">
                  <SelectValue placeholder="Select a template" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">No Template</SelectItem>
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      {template.name} - {template.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm mb-6">
            <CardHeader>
              <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
                Client Information
              </CardTitle>
              <CardDescription>Basic details about your client and project</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <Label htmlFor="client_name" className="text-slate-700 font-medium mb-2">
                  Client Name *
                </Label>
                <Input
                  id="client_name"
                  name="client_name"
                  value={formData.client_name}
                  onChange={handleChange}
                  placeholder="Enter client name"
                  className="border-slate-200 focus-visible:ring-slate-900"
                  data-testid="client-name-input"
                  required
                />
              </div>

              <div>
                <Label htmlFor="project_description" className="text-slate-700 font-medium mb-2">
                  Project Description *
                </Label>
                <Textarea
                  id="project_description"
                  name="project_description"
                  value={formData.project_description}
                  onChange={handleChange}
                  placeholder="Describe the project scope, goals, and requirements"
                  className="border-slate-200 focus-visible:ring-slate-900 min-h-32"
                  data-testid="project-description-input"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="budget_range" className="text-slate-700 font-medium mb-2">
                    Budget Range *
                  </Label>
                  <Input
                    id="budget_range"
                    name="budget_range"
                    value={formData.budget_range}
                    onChange={handleChange}
                    placeholder="e.g., $50,000 - $75,000"
                    className="border-slate-200 focus-visible:ring-slate-900"
                    data-testid="budget-range-input"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="timeline" className="text-slate-700 font-medium mb-2">
                    Timeline *
                  </Label>
                  <Input
                    id="timeline"
                    name="timeline"
                    value={formData.timeline}
                    onChange={handleChange}
                    placeholder="e.g., 3-4 months"
                    className="border-slate-200 focus-visible:ring-slate-900"
                    data-testid="timeline-input"
                    required
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="deal_value" className="text-slate-700 font-medium mb-2">
                  Estimated Deal Value (Optional)
                </Label>
                <Input
                  id="deal_value"
                  name="deal_value"
                  type="number"
                  value={formData.deal_value}
                  onChange={handleChange}
                  placeholder="e.g., 65000"
                  className="border-slate-200 focus-visible:ring-slate-900"
                  data-testid="deal-value-input"
                />
                <p className="text-xs text-slate-500 mt-1">Used for analytics tracking</p>
              </div>

              <div>
                <Label htmlFor="additional_requirements" className="text-slate-700 font-medium mb-2">
                  Additional Requirements (Optional)
                </Label>
                <Textarea
                  id="additional_requirements"
                  name="additional_requirements"
                  value={formData.additional_requirements}
                  onChange={handleChange}
                  placeholder="Any specific requirements or notes"
                  className="border-slate-200 focus-visible:ring-slate-900"
                  data-testid="additional-requirements-input"
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm mb-6">
            <CardHeader>
              <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
                Upload Requirements Document (Optional)
              </CardTitle>
              <CardDescription>Upload a PDF or TXT file with detailed requirements</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <Label
                  htmlFor="file-upload"
                  className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-md cursor-pointer hover:bg-slate-50 transition-colors"
                >
                  <Upload className="h-4 w-4" />
                  Choose File
                </Label>
                <Input
                  id="file-upload"
                  type="file"
                  accept=".pdf,.txt"
                  onChange={handleFileUpload}
                  className="hidden"
                  data-testid="file-upload-input"
                />
                {uploading && (
                  <div className="flex items-center gap-2 text-slate-600">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Uploading...
                  </div>
                )}
                {uploadedFile && (
                  <div className="flex items-center gap-2 text-emerald-600">
                    <FileText className="h-4 w-4" />
                    {uploadedFile.name}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm mb-6">
            <CardHeader>
              <CardTitle className="font-outfit text-2xl font-semibold text-slate-900">
                Select Clauses
              </CardTitle>
              <CardDescription>
                Choose pre-defined clauses to include in your proposal
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ClauseSelector
                selectedClauses={formData.selected_clauses}
                onClausesChange={handleClausesChange}
              />
            </CardContent>
          </Card>

          <div className="flex justify-end gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate('/dashboard')}
              disabled={loading || generating}
              data-testid="cancel-button"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-slate-900 text-white hover:bg-slate-800"
              disabled={loading || generating}
              data-testid="generate-button"
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating with AI...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate Proposal
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateProposal;