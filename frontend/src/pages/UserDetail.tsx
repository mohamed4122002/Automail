import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ArrowLeft, Mail, Clock, Calendar, MessageSquare } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../lib/api";

function MousePointerIcon() { return <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" /></svg> }
function MailOpenIcon() { return <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" /></svg> }
function SendIcon() { return <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg> }
function UserPlusIcon() { return <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" /></svg> }

const UserDetail: React.FC = () => {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const [noteContent, setNoteContent] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ['user', id],
    queryFn: async () => {
      // In a real app we'd use the actual ID from params.
      // For demo since we seeded consistent IDs, let's just fetch proper mock data from backend
      // or if ID is 101, etc.
      const res = await api.get(`/users/${id || 'default'}`);
      return res.data;
    },
    enabled: !!id,
  });

  const createNoteMutation = useMutation({
    mutationFn: async (content: string) => {
      return await api.post(`/users/${id}/notes`, { content });
    },
    onSuccess: () => {
      setNoteContent("");
      queryClient.invalidateQueries({ queryKey: ['user', id] });
    }
  });

  if (isLoading) return <div className="p-8 text-center">Loading profile...</div>;
  if (error || !data) return <div className="p-8 text-center text-red-400">User not found</div>;

  const { user, timeline, notes } = data;

  const claimMutation = useMutation({
    mutationFn: async () => {
      return await api.post(`/users/${id}/claim`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user', id] });
    }
  });

  const getIcon = (type: string) => {
    switch (type) {
      case 'click': return <MousePointerIcon />;
      case 'open': return <MailOpenIcon />;
      case 'sent': return <SendIcon />;
      case 'signup': return <UserPlusIcon />;
      default: return <Clock className="w-3 h-3" />;
    }
  };

  return (
    <Layout title="User Profile">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: User Info */}
        <div className="lg:col-span-1 space-y-6">
          <Link to="/users">
            <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="w-4 h-4" />} className="mb-4">Back to Users</Button>
          </Link>

          <Card>
            <CardContent className="flex flex-col items-center pt-8">
              <div className="w-24 h-24 rounded-full bg-slate-700 flex items-center justify-center text-3xl font-bold text-slate-300 mb-4 ring-4 ring-slate-800">
                {user.first_name?.[0] || user.email[0]}
              </div>
              <h2 className="text-xl font-bold text-slate-100">{user.first_name} {user.last_name}</h2>
              <p className="text-slate-400 text-sm mb-4">{user.company || "No Company"}</p>
              <div className="flex gap-2 mb-4">
                <Badge variant={user.is_active ? "success" : "neutral"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
                <Badge variant="neutral">Subscriber</Badge>
              </div>

              {user.claimed_by_id ? (
                <div className="text-xs text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-full border border-emerald-500/20 mb-6 flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Claimed at {new Date(user.claimed_at).toLocaleDateString()}
                </div>
              ) : (
                <div className="text-xs text-slate-500 bg-slate-500/10 px-3 py-1.5 rounded-full border border-slate-500/20 mb-6">
                  Currently Unclaimed
                </div>
              )}

              <div className="w-full space-y-4 border-t border-slate-700 pt-6">
                <div className="flex items-center text-sm text-slate-300">
                  <Mail className="w-4 h-4 mr-3 text-slate-500" />
                  {user.email}
                </div>
                <div className="flex items-center text-sm text-slate-300">
                  <Calendar className="w-4 h-4 mr-3 text-slate-500" />
                  Joined {new Date(user.created_at).toLocaleDateString()}
                </div>
                <div className="flex items-center text-sm text-slate-300">
                  <Clock className="w-4 h-4 mr-3 text-slate-500" />
                  Last Active: Recent
                </div>
              </div>

              <div className="w-full mt-8 flex flex-col gap-2">
                {!user.claimed_by_id && (
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => claimMutation.mutate()}
                    isLoading={claimMutation.isPending}
                  >
                    Claim Lead
                  </Button>
                )}
                <Button variant="secondary" className="w-full">Edit Profile</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Follow-up Notes</CardTitle></CardHeader>
            <CardContent>
              <div className="mb-4 max-h-40 overflow-y-auto space-y-2">
                {notes.length === 0 && <p className="text-xs text-slate-500 italic">No notes yet.</p>}
                {notes.map((note: any) => (
                  <div key={note.id} className="bg-slate-900/50 p-2 rounded border border-slate-800 text-sm">
                    <p className="text-slate-300">{note.content}</p>
                    <span className="text-[10px] text-slate-500">{new Date(note.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
              <textarea
                className="w-full h-24 bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-slate-300 focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
                placeholder="Add private notes here..."
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
              ></textarea>
              <div className="flex justify-end mt-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => createNoteMutation.mutate(noteContent)}
                  isLoading={createNoteMutation.isPending}
                  disabled={!noteContent.trim()}
                >
                  Save Note
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Timeline */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Interaction Timeline</CardTitle>
              <Button variant="ghost" size="sm" leftIcon={<MessageSquare className="w-4 h-4" />}>Log Activity</Button>
            </CardHeader>
            <CardContent>
              <div className="relative border-l border-slate-800 ml-3 space-y-8 py-2">
                {timeline.map((item: any) => (
                  <div key={item.id} className="relative pl-8">
                    <span className="absolute -left-3 top-0 flex items-center justify-center w-6 h-6 bg-slate-900 rounded-full ring-4 ring-slate-900">
                      <div className="w-6 h-6 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400">
                        {getIcon(item.icon_type || 'clock')}
                      </div>
                    </span>
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                      <h3 className="text-sm font-medium text-slate-200">{item.content}</h3>
                      <time className="text-xs text-slate-500 mt-1 sm:mt-0">{item.date}</time>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default UserDetail;
