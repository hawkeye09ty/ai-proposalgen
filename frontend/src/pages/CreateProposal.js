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
    template_id: '',
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

  const handleGenerateAndSave = async (e) => {
    e.preventDefault();

    if (!formData.client_name || !formData.project_description || !formData.budget_range || !formData.timeline) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setGenerating(true);
      
      // AI generation can take time, so we increase the timeout to 120 seconds
      const generateResponse = await axios.post(`${API}/generate-proposal`, formData, {
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
        status: 'Draft'
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