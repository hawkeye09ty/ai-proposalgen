import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Settings as SettingsIcon, Mail, Link2, FileText, Save, Loader2, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Settings = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [integrationStatus, setIntegrationStatus] = useState({
    resend: { connected: false, checking: false },
    brevo: { connected: false, checking: false },
    google: { connected: false, checking: false }
  });
  
  const [settings, setSettings] = useState({
    company_name: 'ProposalAI',
    default_sender_email: '',
    auto_send_on_approval: false,
    brevo_polling_enabled: true,
    brevo_polling_interval: 5,
    google_doc_template_id: '',
    approval_keyword: 'APPROVED',
    notify_on_proposal_open: true,
    notify_on_proposal_click: true
  });

  useEffect(() => {
    fetchSettings();
    checkIntegrations();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/settings`);
      if (response.data) {
        setSettings(prev => ({ ...prev, ...response.data }));
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
      // Settings might not exist yet, that's ok
    } finally {
      setLoading(false);
    }
  };

  const checkIntegrations = async () => {
    // Check Resend
    setIntegrationStatus(prev => ({ ...prev, resend: { ...prev.resend, checking: true } }));
    try {
      const resendRes = await axios.get(`${API}/integrations/resend/status`);
      setIntegrationStatus(prev => ({ 
        ...prev, 
        resend: { connected: resendRes.data.connected, checking: false } 
      }));
    } catch {
      setIntegrationStatus(prev => ({ ...prev, resend: { connected: false, checking: false } }));
    }

    // Check Brevo
    setIntegrationStatus(prev => ({ ...prev, brevo: { ...prev.brevo, checking: true } }));
    try {
      const brevoRes = await axios.get(`${API}/integrations/brevo/status`);
      setIntegrationStatus(prev => ({ 
        ...prev, 
        brevo: { connected: brevoRes.data.connected, checking: false } 
      }));
    } catch {
      setIntegrationStatus(prev => ({ ...prev, brevo: { connected: false, checking: false } }));
    }

    // Check Google
    setIntegrationStatus(prev => ({ ...prev, google: { ...prev.google, checking: true } }));
    try {
      const googleRes = await axios.get(`${API}/integrations/google/status`);
      setIntegrationStatus(prev => ({ 
        ...prev, 
        google: { connected: googleRes.data.connected, checking: false } 
      }));
    } catch {
      setIntegrationStatus(prev => ({ ...prev, google: { connected: false, checking: false } }));
    }
  };

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      await axios.post(`${API}/settings`, settings);
      toast.success('Settings saved successfully');
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const IntegrationStatusBadge = ({ status }) => {
    if (status.checking) {
      return (
        <Badge variant="outline" className="bg-slate-50 text-slate-600">
          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          Checking...
        </Badge>
      );
    }
    
    if (status.connected) {
      return (
        <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200">
          <CheckCircle className="h-3 w-3 mr-1" />
          Connected
        </Badge>
      );
    }
    
    return (
      <Badge className="bg-red-50 text-red-700 border-red-200">
        <XCircle className="h-3 w-3 mr-1" />
        Not Connected
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto mb-4"></div>
          <p className="text-slate-600">Loading settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8" data-testid="settings-page">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="font-outfit text-4xl font-semibold tracking-tight text-slate-900 mb-2">
              Settings
            </h1>
            <p className="text-slate-600">Configure your ProposalAI integrations and preferences</p>
          </div>
          <Button
            onClick={handleSaveSettings}
            disabled={saving}
            className="bg-slate-900 text-white hover:bg-slate-800"
            data-testid="save-settings-button"
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Settings
              </>
            )}
          </Button>
        </div>

        {/* Integration Status */}
        <Card className="border-slate-200 shadow-sm mb-6">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="font-outfit text-xl font-semibold text-slate-900 flex items-center gap-2">
                  <Link2 className="h-5 w-5" />
                  Integration Status
                </CardTitle>
                <CardDescription>Monitor your connected services</CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={checkIntegrations}
                data-testid="refresh-integrations-button"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-slate-600" />
                  <span className="font-medium text-slate-900">Resend (Email)</span>
                </div>
                <IntegrationStatusBadge status={integrationStatus.resend} />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                <div className="flex items-center gap-3">
                  <Link2 className="h-5 w-5 text-slate-600" />
                  <span className="font-medium text-slate-900">Brevo (CRM)</span>
                </div>
                <IntegrationStatusBadge status={integrationStatus.brevo} />
              </div>
              
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-200">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-slate-600" />
                  <span className="font-medium text-slate-900">Google Docs</span>
                </div>
                <IntegrationStatusBadge status={integrationStatus.google} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* General Settings */}
        <Card className="border-slate-200 shadow-sm mb-6">
          <CardHeader>
            <CardTitle className="font-outfit text-xl font-semibold text-slate-900 flex items-center gap-2">
              <SettingsIcon className="h-5 w-5" />
              General Settings
            </CardTitle>
            <CardDescription>Configure your basic application settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label htmlFor="company_name">Company Name</Label>
                <Input
                  id="company_name"
                  value={settings.company_name}
                  onChange={(e) => handleInputChange('company_name', e.target.value)}
                  placeholder="Your Company Name"
                  className="border-slate-200 mt-1"
                  data-testid="company-name-input"
                />
              </div>
              <div>
                <Label htmlFor="default_sender_email">Default Sender Email</Label>
                <Input
                  id="default_sender_email"
                  type="email"
                  value={settings.default_sender_email}
                  onChange={(e) => handleInputChange('default_sender_email', e.target.value)}
                  placeholder="proposals@yourcompany.com"
                  className="border-slate-200 mt-1"
                  data-testid="sender-email-input"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Email Notifications */}
        <Card className="border-slate-200 shadow-sm mb-6">
          <CardHeader>
            <CardTitle className="font-outfit text-xl font-semibold text-slate-900 flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Email Notifications
            </CardTitle>
            <CardDescription>Configure email tracking notifications</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="font-medium">Notify on Proposal Open</Label>
                <p className="text-sm text-slate-500">Get notified when a client opens your proposal email</p>
              </div>
              <Switch
                checked={settings.notify_on_proposal_open}
                onCheckedChange={(checked) => handleInputChange('notify_on_proposal_open', checked)}
                data-testid="notify-open-switch"
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label className="font-medium">Notify on Link Click</Label>
                <p className="text-sm text-slate-500">Get notified when a client clicks the proposal link</p>
              </div>
              <Switch
                checked={settings.notify_on_proposal_click}
                onCheckedChange={(checked) => handleInputChange('notify_on_proposal_click', checked)}
                data-testid="notify-click-switch"
              />
            </div>
          </CardContent>
        </Card>

        {/* Brevo Integration */}
        <Card className="border-slate-200 shadow-sm mb-6">
          <CardHeader>
            <CardTitle className="font-outfit text-xl font-semibold text-slate-900 flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              Brevo Integration
            </CardTitle>
            <CardDescription>Configure CRM automation settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="font-medium">Enable Polling</Label>
                <p className="text-sm text-slate-500">Automatically check Brevo for opportunities in "proposal" stage</p>
              </div>
              <Switch
                checked={settings.brevo_polling_enabled}
                onCheckedChange={(checked) => handleInputChange('brevo_polling_enabled', checked)}
                data-testid="brevo-polling-switch"
              />
            </div>
            <Separator />
            <div>
              <Label htmlFor="brevo_polling_interval">Polling Interval (minutes)</Label>
              <Input
                id="brevo_polling_interval"
                type="number"
                min={1}
                max={60}
                value={settings.brevo_polling_interval}
                onChange={(e) => handleInputChange('brevo_polling_interval', parseInt(e.target.value) || 5)}
                className="border-slate-200 mt-1 w-32"
                data-testid="polling-interval-input"
              />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div>
                <Label className="font-medium">Auto-send on Approval</Label>
                <p className="text-sm text-slate-500">Automatically send proposal when marked as approved</p>
              </div>
              <Switch
                checked={settings.auto_send_on_approval}
                onCheckedChange={(checked) => handleInputChange('auto_send_on_approval', checked)}
                data-testid="auto-send-switch"
              />
            </div>
          </CardContent>
        </Card>

        {/* Google Docs Integration */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="font-outfit text-xl font-semibold text-slate-900 flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Google Docs Integration
            </CardTitle>
            <CardDescription>Configure document automation settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <Label htmlFor="google_doc_template_id">Google Doc Template ID</Label>
              <Input
                id="google_doc_template_id"
                value={settings.google_doc_template_id}
                onChange={(e) => handleInputChange('google_doc_template_id', e.target.value)}
                placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
                className="border-slate-200 mt-1"
                data-testid="google-template-input"
              />
              <p className="text-xs text-slate-500 mt-1">
                The ID from your Google Docs template URL
              </p>
            </div>
            <Separator />
            <div>
              <Label htmlFor="approval_keyword">Approval Keyword</Label>
              <Input
                id="approval_keyword"
                value={settings.approval_keyword}
                onChange={(e) => handleInputChange('approval_keyword', e.target.value)}
                placeholder="APPROVED"
                className="border-slate-200 mt-1 w-48"
                data-testid="approval-keyword-input"
              />
              <p className="text-xs text-slate-500 mt-1">
                Comment keyword that triggers document approval
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Settings;
