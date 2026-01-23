import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { ArrowLeft, Edit, Save, FileDown, Loader2, Mail, Eye, MousePointerClick } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import jsPDF from 'jspdf';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const ProposalDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [proposal, setProposal] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [emailDialogOpen, setEmailDialogOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [emailLogs, setEmailLogs] = useState([]);
  const [emailForm, setEmailForm] = useState({
    recipient_email: '',
    custom_message: ''
  });

  useEffect(() => {
    fetchProposal();
    fetchEmailLogs();
  }, [id]);

  const fetchProposal = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/proposals/${id}`);
      setProposal(response.data);
      setEditedContent(response.data.content || '');
    } catch (error) {
      console.error('Error fetching proposal:', error);
      toast.error('Failed to load proposal');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchEmailLogs = async () => {
    try {
      const response = await axios.get(`${API}/email-logs/${id}`);
      setEmailLogs(response.data);
    } catch (error) {
      console.error('Error fetching email logs:', error);
    }
  };

  const handleStatusChange = async (newStatus) => {
    try {
      await axios.patch(`${API}/proposals/${id}`, { status: newStatus });
      setProposal({ ...proposal, status: newStatus });
      toast.success('Status updated successfully');
    } catch (error) {
      console.error('Error updating status:', error);
      toast.error('Failed to update status');
    }
  };

  const handleSaveContent = async () => {
    try {
      setSaving(true);
      await axios.patch(`${API}/proposals/${id}`, { content: editedContent });
      setProposal({ ...proposal, content: editedContent });
      setEditing(false);
      toast.success('Proposal updated successfully');
    } catch (error) {
      console.error('Error saving proposal:', error);
      toast.error('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = () => {
    try {
      const pdf = new jsPDF();
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 20;
      const maxWidth = pageWidth - (margin * 2);
      
      // Title
      pdf.setFontSize(20);
      pdf.setFont(undefined, 'bold');
      pdf.text(`Proposal for ${proposal.client_name}`, margin, margin);
      
      // Metadata
      pdf.setFontSize(10);
      pdf.setFont(undefined, 'normal');
      pdf.text(`Budget: ${proposal.budget_range}`, margin, margin + 10);
      pdf.text(`Timeline: ${proposal.timeline}`, margin, margin + 15);
      pdf.text(`Status: ${proposal.status}`, margin, margin + 20);
      
      // Content
      pdf.setFontSize(11);
      const lines = pdf.splitTextToSize(proposal.content, maxWidth);
      let yPosition = margin + 30;
      
      lines.forEach((line) => {
        if (yPosition > pageHeight - margin) {
          pdf.addPage();
          yPosition = margin;
        }
        pdf.text(line, margin, yPosition);
        yPosition += 6;
      });
      
      pdf.save(`${proposal.client_name.replace(/\s+/g, '_')}_Proposal.pdf`);
      toast.success('Proposal exported as PDF successfully');
    } catch (error) {
      console.error('Error exporting PDF:', error);
      toast.error('Failed to export PDF');
    }
  };

  const getStatusBadgeClass = (status) => {
    const classes = {
      'Draft': 'bg-slate-100 text-slate-700 border-slate-200',
      'Pending Review': 'bg-amber-50 text-amber-700 border-amber-200',
      'Sent': 'bg-blue-50 text-blue-700 border-blue-200',
      'Accepted': 'bg-emerald-50 text-emerald-700 border-emerald-200',
      'Rejected': 'bg-red-50 text-red-700 border-red-200'
    };
    return classes[status] || classes['Draft'];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading proposal...</p>
        </div>
      </div>
    );
  }

  if (!proposal) return null;

  return (
    <div className="p-8" data-testid="proposal-detail-page">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard')}
            className="mb-4"
            data-testid="back-to-dashboard-button"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>

          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="font-outfit text-4xl font-semibold tracking-tight text-slate-900 mb-2">
                {proposal.client_name}
              </h1>
              <p className="text-slate-600">{proposal.project_description}</p>
            </div>
            <Badge className={`status-badge ${getStatusBadgeClass(proposal.status)}`} data-testid="proposal-status-badge">
              {proposal.status}
            </Badge>
          </div>

          <div className="flex gap-4 mb-6">
            <Select value={proposal.status} onValueChange={handleStatusChange}>
              <SelectTrigger className="w-48" data-testid="status-select">
                <SelectValue placeholder="Change status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Draft">Draft</SelectItem>
                <SelectItem value="Pending Review">Pending Review</SelectItem>
                <SelectItem value="Sent">Sent</SelectItem>
                <SelectItem value="Accepted">Accepted</SelectItem>
                <SelectItem value="Rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>

            {!editing ? (
              <>
                <Button
                  variant="outline"
                  onClick={() => setEditing(true)}
                  data-testid="edit-proposal-button"
                >
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Content
                </Button>
                <Button
                  variant="outline"
                  onClick={handleExport}
                  data-testid="export-button"
                >
                  <FileDown className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </>
            ) : (
              <>
                <Button
                  onClick={handleSaveContent}
                  className="bg-slate-900 text-white hover:bg-slate-800"
                  disabled={saving}
                  data-testid="save-proposal-button"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Changes
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setEditing(false);
                    setEditedContent(proposal.content);
                  }}
                  disabled={saving}
                  data-testid="cancel-edit-button"
                >
                  Cancel
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="border-slate-200">
            <CardContent className="p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Budget</p>
              <p className="font-semibold text-slate-900">{proposal.budget_range}</p>
            </CardContent>
          </Card>
          <Card className="border-slate-200">
            <CardContent className="p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Timeline</p>
              <p className="font-semibold text-slate-900">{proposal.timeline}</p>
            </CardContent>
          </Card>
          <Card className="border-slate-200">
            <CardContent className="p-4">
              <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">Created</p>
              <p className="font-semibold text-slate-900">
                {new Date(proposal.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric'
                })}
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="border-slate-200">
          <CardContent className="p-8">
            {editing ? (
              <Textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="min-h-[600px] font-sans border-slate-200 focus-visible:ring-slate-900"
                data-testid="proposal-content-editor"
              />
            ) : (
              <div 
                className="proposal-content prose max-w-none" 
                data-testid="proposal-content-display"
                style={{ whiteSpace: 'pre-wrap' }}
              >
                {proposal.content || 'No content available'}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ProposalDetail;