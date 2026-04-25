"""
AI Chatbot Module for SkillGap Analyzer
Provides intelligent, context-aware responses using OpenAI API
with fallback to rule-based responses if API unavailable
"""

import openai
from config import Config
from database.db import get_db


class AIChat:
    """Unified AI Chatbot Handler"""
    
    def __init__(self):
        if Config.OPENAI_API_KEY:
            openai.api_key = Config.OPENAI_API_KEY
            self.api_available = True
        else:
            self.api_available = False
    
    @staticmethod
    def get_user_context(user_id: int, category: str = None) -> dict:
        """
        Fetch user's performance context from database
        
        Args:
            user_id: User ID
            category: Specific interview category (optional)
            
        Returns:
            Dictionary with user stats and analysis
        """
        db = get_db()
        try:
            # Get interview performance
            if category:
                sessions = db.execute(
                    '''SELECT AVG(avg_score) as avg_score, COUNT(*) as total_sessions 
                       FROM interview_sessions 
                       WHERE user_id = ? AND category = ?''',
                    (user_id, category)
                ).fetchone()
            else:
                sessions = db.execute(
                    '''SELECT AVG(avg_score) as avg_score, COUNT(*) as total_sessions 
                       FROM interview_sessions 
                       WHERE user_id = ? AND completed = 1''',
                    (user_id,)
                ).fetchone()
            
            avg_score = sessions['avg_score'] or 0
            total_sessions = sessions['total_sessions'] or 0
            
            # Get latest skill analysis
            skill_analysis = db.execute(
                '''SELECT matched_skills, missing_skills, overall_score 
                   FROM skill_analyses 
                   WHERE user_id = ? 
                   ORDER BY created_at DESC LIMIT 1''',
                (user_id,)
            ).fetchone()
            
            matched_skills = []
            missing_skills = []
            
            if skill_analysis:
                import json
                try:
                    matched_skills = json.loads(skill_analysis['matched_skills']) if skill_analysis['matched_skills'] else []
                    missing_skills = json.loads(skill_analysis['missing_skills']) if skill_analysis['missing_skills'] else []
                except:
                    pass
            
            # Get recent answers to identify strengths/weaknesses
            answers = db.execute(
                '''SELECT result_category, COUNT(*) as count, AVG(score) as avg 
                   FROM answers 
                   WHERE user_id = ? 
                   GROUP BY result_category 
                   ORDER BY avg DESC''',
                (user_id,)
            ).fetchall()
            
            strong_areas = [a['result_category'] for a in answers[:2]] if answers else []
            weak_areas = [a['result_category'] for a in answers[-2:]] if answers else []
            
            return {
                'avg_score': round(avg_score, 1),
                'total_sessions': total_sessions,
                'matched_skills': matched_skills[:5],  # Top 5
                'missing_skills': missing_skills[:5],
                'strong_areas': strong_areas,
                'weak_areas': weak_areas,
                'category': category or 'general'
            }
        except Exception as e:
            print(f"Error fetching user context: {e}")
            return {
                'avg_score': 0,
                'total_sessions': 0,
                'matched_skills': [],
                'missing_skills': [],
                'strong_areas': [],
                'weak_areas': [],
                'category': category or 'general'
            }
        finally:
            db.close()
    
    def build_system_prompt(self, user_context: dict, mode: str = 'session') -> str:
        """
        Build comprehensive system prompt with user context
        
        Args:
            user_context: User's performance context
            mode: 'session' (post-interview) or 'dashboard' (general)
            
        Returns:
            System prompt string
        """
        
        # Use .get() with defaults to prevent KeyError
        matched_skills = user_context.get('matched_skills', [])
        missing_skills = user_context.get('missing_skills', [])
        strong_areas = user_context.get('strong_areas', [])
        weak_areas = user_context.get('weak_areas', [])
        avg_score = user_context.get('avg_score', 0)
        total_sessions = user_context.get('total_sessions', 0)
        category = user_context.get('category', 'general')
        
        matched_skills_str = ', '.join(matched_skills) if matched_skills else 'None identified yet'
        missing_skills_str = ', '.join(missing_skills) if missing_skills else 'None identified yet'
        strong_areas_str = ', '.join(strong_areas) if strong_areas else 'Multiple areas'
        weak_areas_str = ', '.join(weak_areas) if weak_areas else 'Continue practicing'
        
        system_prompt = f"""You are SkillGap AI, an intelligent career development assistant for the SkillGap Analyzer platform.

PLATFORM OVERVIEW:
SkillGap Analyzer is a comprehensive web application that helps users:
- Assess skill gaps through AI-powered semantic analysis
- Practice technical interviews with real-time AI feedback
- Analyze code quality via GitHub repository integration
- Generate personalized 30-day learning plans
- Track performance across multiple sessions
- Export professional PDF reports

KEY FEATURES:
1. Skill Gap Analysis: Semantic skill matching with job requirements
2. Interview Practice: 10-question sessions with AI evaluation (Technical, HR, DSA, Database, Soft Skills)
3. GitHub Analyzer: Repository code quality assessment
4. Learning Planner: Structured 30-day improvement roadmaps
5. Dashboard: Performance analytics and trends
6. PDF Reports: Professional progress documentation

USER'S CURRENT PROFILE:
- Average Score: {avg_score}/100
- Completed Sessions: {total_sessions}
- Category: {category}
- Matched Skills: {matched_skills_str}
- Missing Skills (Gap Areas): {missing_skills_str}
- Strong Areas: {strong_areas_str}
- Areas for Improvement: {weak_areas_str}

INTERACTION CONTEXT:
- Mode: {mode}
- Purpose: {'Provide targeted post-interview coaching' if mode == 'session' else 'General career guidance and platform support'}

RESPONSE GUIDELINES:
1. Be encouraging, professional, and specific
2. Personalize advice using user's skills and performance
3. Keep responses concise (max 150 words) and actionable
4. If user mentions a weak area, suggest specific platform features
5. Reference the 30-day planner or interview practice when relevant
6. Use STAR method for behavioral questions when discussing interview prep
7. Maintain conversation context from chat history
8. If unsure, ask clarifying questions to provide better guidance

TONE: Supportive mentor who understands career development challenges"""
        
        return system_prompt
    
    def generate_response(self, 
                         message: str, 
                         user_id: int,
                         context: dict = None,
                         history: list = None,
                         mode: str = 'session') -> str:
        """
        Generate AI response with context awareness
        
        Args:
            message: User's question/message
            user_id: User ID for context fetching
            context: Optional pre-computed context
            history: Conversation history (list of dicts with 'role' and 'content')
            mode: 'session' or 'dashboard'
            
        Returns:
            AI-generated response string
        """
        
        if not message or not message.strip():
            return "Please ask me something! I'm here to help with interview prep, skill development, and career guidance."
        
        # Get or use provided context
        if not context:
            category = None
            if history and len(history) > 0:
                # Try to infer category from history
                category = None  # Can be enhanced based on conversation
            context = self.get_user_context(user_id, category)
        
        # Try AI if available
        if self.api_available:
            return self._openai_response(message, context, history or [], mode)
        else:
            # Fallback to rule-based
            return self._rule_based_response(message, context, mode)
    
    def _openai_response(self, 
                        message: str, 
                        context: dict, 
                        history: list,
                        mode: str) -> str:
        """
        Get response from OpenAI API
        
        Args:
            message: User message
            context: User context dict
            history: Conversation history
            mode: 'session' or 'dashboard'
            
        Returns:
            Response string
        """
        try:
            system_prompt = self.build_system_prompt(context, mode)
            
            # Build messages list
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (last 8 messages)
            for item in history[-8:]:
                if 'role' in item and 'content' in item:
                    messages.append({"role": item["role"], "content": item["content"]})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Call OpenAI
            response = openai.ChatCompletion.create(
                model=Config.CHATBOT_MODEL,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                top_p=0.9
            )
            
            reply = response.choices[0].message.content.strip()
            return reply
            
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            # Fallback to rule-based
            return self._rule_based_response(message, context, mode)
    
    def _rule_based_response(self, 
                            message: str, 
                            context: dict,
                            mode: str) -> str:
        """
        Fallback rule-based chatbot response
        
        Args:
            message: User message
            context: User context dict
            mode: 'session' or 'dashboard'
            
        Returns:
            Response string
        """
        msg_lower = message.lower()
        avg = context.get('avg_score', 0)
        weak_areas = context.get('weak_areas', [])
        strong_areas = context.get('strong_areas', [])
        matched_skills = context.get('matched_skills', [])
        missing_skills = context.get('missing_skills', [])
        
        # Platform info questions
        if any(word in msg_lower for word in ['what is', 'about', 'platform', 'app', 'skillgap']):
            return ("SkillGap Analyzer is an AI-powered career development platform. It helps you: "
                   "1) Identify skill gaps through semantic analysis, 2) Practice interviews with AI feedback, "
                   "3) Analyze GitHub projects, 4) Create 30-day learning plans, 5) Track progress. "
                   "Start with skill analysis or interview practice!")
        
        if any(word in msg_lower for word in ['feature', 'work', 'how does']):
            return ("Key features: Skill Gap Analysis (matches your skills to job roles), "
                   "Interview Practice (10-question sessions with real-time feedback), "
                   "GitHub Analyzer (evaluates your code repositories), "
                   "30-Day Learning Plans (structured improvement paths), "
                   "Performance Dashboard (track progress over time).")
        
        # Performance feedback
        if any(word in msg_lower for word in ['score', 'low', 'why', 'bad', 'poor']):
            if avg < 50:
                return (f"Your {avg}/100 score shows opportunities for growth. Focus areas: "
                       f"{weak_areas[0] if weak_areas else 'core concepts'}. "
                       f"Practice daily in our interview simulator and review weak areas.")
            elif avg < 70:
                return (f"Good progress with {avg}/100! Strengths: {strong_areas[0] if strong_areas else 'solid foundation'}. "
                       f"Next: Improve {weak_areas[0] if weak_areas else 'consistency'} with targeted practice.")
            else:
                return (f"Excellent {avg}/100! Keep polishing {weak_areas[0] if weak_areas else 'edge cases'} "
                       f"to reach senior-level performance.")
        
        # Improvement advice
        if any(word in msg_lower for word in ['improve', 'better', 'help', 'tips', 'advice', 'how']):
            gap_area = missing_skills[0] if missing_skills else (weak_areas[0] if weak_areas else 'fundamentals')
            return (f"To improve: 1) Practice mock interviews daily (focus: {gap_area}), "
                   f"2) Use STAR method for behavioral questions, "
                   f"3) Follow the 30-Day Learning Plan, "
                   f"4) Review past session feedback. "
                   f"Your matched skills: {', '.join(matched_skills[:2]) if matched_skills else 'build on current foundation'}.")
        
        # Learning resources
        if any(word in msg_lower for word in ['next', 'learn', 'study', 'plan', 'resource', 'course']):
            focus_area = missing_skills[0] if missing_skills else 'advanced concepts'
            return (f"Next steps: Master {focus_area}. Resources: LeetCode (DSA), Coursera, freeCodeCamp. "
                   f"Use our 30-Day Planner for day-wise structure with resources. "
                   f"After each session, review your feedback carefully.")
        
        # Strengths and motivation
        if any(word in msg_lower for word in ['strength', 'good', 'strong', 'well', 'motivat']):
            strengths = ', '.join(matched_skills[:2]) if matched_skills else 'consistent effort and determination'
            return (f"Your strengths: {strengths}. Build on these to reach your target role. "
                   f"Every expert started where you are. Your {avg}/100 score shows real potential — keep improving!")
        
        # Technical stack
        if any(word in msg_lower for word in ['tech', 'stack', 'built', 'python', 'flask']):
            return ("Built with Flask (Python backend), SQLite, and ML models (Sentence Transformers, scikit-learn). "
                   "Features real-time AI feedback, semantic skill matching, GitHub integration, and PDF reports. "
                   "Fully production-ready and scalable!")
        
        # Default helpful response
        return (f"I'm your SkillGap AI coach! I can help with interview prep, skill analysis, "
               f"learning plans, and platform questions. Your current score: {avg}/100. "
               f"What would you like to know?")


# Convenience functions
def get_ai_response(message: str, user_id: int, context: dict = None, 
                   history: list = None, mode: str = 'session') -> str:
    """
    Convenience function to generate AI response
    
    Usage:
        response = get_ai_response(
            message="How can I improve my score?",
            user_id=1,
            mode='session'
        )
    """
    chatbot = AIChat()
    return chatbot.generate_response(message, user_id, context, history, mode)


def get_user_chat_context(user_id: int, category: str = None) -> dict:
    """
    Convenience function to get user context
    
    Usage:
        context = get_user_chat_context(user_id=1, category='Technical')
    """
    return AIChat.get_user_context(user_id, category)
