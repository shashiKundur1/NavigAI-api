# src/firebase_db/analytics.py
"""
Firebase operations for analytics data in NavigAI
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.cloud.firestore import FieldFilter, Query
from google.cloud import firestore
import statistics

from .firebase_init import (
    get_db,
    get_collection,
    COLLECTIONS,
    DocumentNotFoundError,
    ValidationError,
)
from models.interview import InterviewStatus

logger = logging.getLogger(__name__)


async def get_analytics_data(user_id: str) -> Dict[str, Any]:
    """
    Get comprehensive analytics data for a user

    Args:
        user_id (str): User ID to get analytics for

    Returns:
        Dict[str, Any]: User analytics data
    """
    try:
        from .interview_sessions import get_sessions_by_user
        from .interview_reports import get_reports_by_user, get_user_report_statistics

        # Get user sessions and reports
        sessions = await get_sessions_by_user(user_id, limit=100)
        reports = await get_reports_by_user(user_id, limit=100)
        report_stats = await get_user_report_statistics(user_id)

        # Calculate basic metrics
        total_sessions = len(sessions)
        completed_sessions = len(
            [s for s in sessions if s.status == InterviewStatus.COMPLETED]
        )
        completion_rate = (
            (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        )

        # Calculate time-based metrics
        total_interview_time = sum(
            s.actual_duration for s in sessions if s.actual_duration > 0
        )
        avg_interview_duration = (
            (total_interview_time / completed_sessions) if completed_sessions > 0 else 0
        )

        # Get recent activity (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_sessions = [
            s for s in sessions if s.created_at and s.created_at > cutoff_date
        ]
        recent_reports = [
            r for r in reports if r.generated_at and r.generated_at > cutoff_date
        ]

        # Calculate improvement trend
        improvement_trend = await calculate_improvement_score(user_id)

        # Most interviewed roles/companies
        job_titles = [s.job_title for s in sessions if s.job_title]
        companies = [s.company_name for s in sessions if s.company_name]

        job_title_counts = {}
        company_counts = {}

        for title in job_titles:
            job_title_counts[title] = job_title_counts.get(title, 0) + 1

        for company in companies:
            company_counts[company] = company_counts.get(company, 0) + 1

        # Sort by frequency
        top_job_titles = sorted(
            job_title_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_companies = sorted(
            company_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]

        analytics_data = {
            "user_id": user_id,
            "total_interviews": total_sessions,
            "completed_interviews": completed_sessions,
            "completion_rate": round(completion_rate, 2),
            "total_interview_time_minutes": round(total_interview_time / 60, 2),
            "average_interview_duration_minutes": round(avg_interview_duration / 60, 2),
            "recent_activity_30d": {
                "sessions": len(recent_sessions),
                "reports": len(recent_reports),
            },
            "performance_metrics": {
                "average_overall_score": report_stats.get("average_overall_score", 0),
                "best_score": report_stats.get("best_score", 0),
                "most_recent_score": report_stats.get("most_recent_score", 0),
                "improvement_trend": improvement_trend,
            },
            "top_job_titles": [
                {"title": title, "count": count} for title, count in top_job_titles
            ],
            "top_companies": [
                {"company": company, "count": count} for company, count in top_companies
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Generated analytics data for user {user_id}")
        return analytics_data

    except Exception as e:
        logger.error(f"Error getting analytics data for user {user_id}: {e}")
        raise


async def get_performance_trends(user_id: str, days: int = 90) -> Dict[str, Any]:
    """
    Get performance trends over time for a user

    Args:
        user_id (str): User ID to get trends for
        days (int): Number of days to look back

    Returns:
        Dict[str, Any]: Performance trends data
    """
    try:
        from .interview_reports import get_reports_by_user

        # Get reports from the specified time period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        reports = await get_reports_by_user(user_id, limit=100)

        # Filter reports within time period
        filtered_reports = [
            r for r in reports if r.generated_at and r.generated_at > cutoff_date
        ]

        if not filtered_reports:
            return {
                "user_id": user_id,
                "period_days": days,
                "data_points": 0,
                "trends": {},
                "generated_at": datetime.utcnow().isoformat(),
            }

        # Sort reports by date
        filtered_reports.sort(key=lambda x: x.generated_at)

        # Group by week for trend analysis
        weekly_data = {}
        for report in filtered_reports:
            # Get Monday of the week
            week_start = report.generated_at - timedelta(
                days=report.generated_at.weekday()
            )
            week_key = week_start.strftime("%Y-%m-%d")

            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "overall_scores": [],
                    "communication_scores": [],
                    "technical_scores": [],
                    "behavioral_scores": [],
                    "count": 0,
                }

            weekly_data[week_key]["overall_scores"].append(report.overall_score)
            weekly_data[week_key]["communication_scores"].append(
                report.communication_score
            )
            weekly_data[week_key]["technical_scores"].append(report.technical_score)
            weekly_data[week_key]["behavioral_scores"].append(report.behavioral_score)
            weekly_data[week_key]["count"] += 1

        # Calculate weekly averages
        trend_data = []
        for week, data in sorted(weekly_data.items()):
            trend_data.append(
                {
                    "week": week,
                    "interview_count": data["count"],
                    "average_overall_score": round(
                        sum(data["overall_scores"]) / len(data["overall_scores"]), 2
                    ),
                    "average_communication_score": round(
                        sum(data["communication_scores"])
                        / len(data["communication_scores"]),
                        2,
                    ),
                    "average_technical_score": round(
                        sum(data["technical_scores"]) / len(data["technical_scores"]), 2
                    ),
                    "average_behavioral_score": round(
                        sum(data["behavioral_scores"]) / len(data["behavioral_scores"]),
                        2,
                    ),
                }
            )

        # Calculate overall trends
        if len(trend_data) >= 2:
            first_half = trend_data[: len(trend_data) // 2]
            second_half = trend_data[len(trend_data) // 2 :]

            first_avg = sum(week["average_overall_score"] for week in first_half) / len(
                first_half
            )
            second_avg = sum(
                week["average_overall_score"] for week in second_half
            ) / len(second_half)

            improvement_rate = second_avg - first_avg
        else:
            improvement_rate = 0.0

        trends_data = {
            "user_id": user_id,
            "period_days": days,
            "data_points": len(filtered_reports),
            "weekly_trends": trend_data,
            "overall_improvement_rate": round(improvement_rate, 2),
            "total_weeks": len(weekly_data),
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Generated performance trends for user {user_id}")
        return trends_data

    except Exception as e:
        logger.error(f"Error getting performance trends for user {user_id}: {e}")
        raise


async def get_job_analytics(
    job_title: str = None, company_name: str = None, limit: int = 100
) -> Dict[str, Any]:
    """
    Get analytics for specific job titles or companies

    Args:
        job_title (str): Job title to analyze
        company_name (str): Company name to analyze
        limit (int): Maximum number of sessions to analyze

    Returns:
        Dict[str, Any]: Job analytics data
    """
    try:
        from .interview_sessions import search_sessions
        from .interview_reports import get_all_interview_reports

        # Search for relevant sessions
        search_term = job_title or company_name
        if not search_term:
            raise ValueError("Either job_title or company_name must be provided")

        sessions = await search_sessions(search_term, limit=limit)

        # Get reports for these sessions
        session_ids = [s.id for s in sessions]
        all_reports = await get_all_interview_reports(
            limit=limit * 2
        )  # Get more to ensure coverage

        # Filter reports that match our sessions
        relevant_reports = [
            r for r in all_reports if r.interview_session_id in session_ids
        ]

        if not relevant_reports:
            return {
                "search_term": search_term,
                "type": "job_title" if job_title else "company",
                "total_interviews": len(sessions),
                "analyzed_reports": 0,
                "analytics": {},
                "generated_at": datetime.utcnow().isoformat(),
            }

        # Calculate analytics
        overall_scores = [r.overall_score for r in relevant_reports]
        communication_scores = [r.communication_score for r in relevant_reports]
        technical_scores = [r.technical_score for r in relevant_reports]
        behavioral_scores = [r.behavioral_score for r in relevant_reports]

        # Collect common strengths and weaknesses
        all_strengths = []
        all_weaknesses = []

        for report in relevant_reports:
            all_strengths.extend(report.strengths)
            all_weaknesses.extend(report.weaknesses)

        # Count frequency of strengths and weaknesses
        strength_counts = {}
        weakness_counts = {}

        for strength in all_strengths:
            strength_counts[strength] = strength_counts.get(strength, 0) + 1

        for weakness in all_weaknesses:
            weakness_counts[weakness] = weakness_counts.get(weakness, 0) + 1

        # Get top 10 most common
        top_strengths = sorted(
            strength_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_weaknesses = sorted(
            weakness_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        analytics = {
            "search_term": search_term,
            "type": "job_title" if job_title else "company",
            "total_interviews": len(sessions),
            "analyzed_reports": len(relevant_reports),
            "score_statistics": {
                "overall": {
                    "average": round(statistics.mean(overall_scores), 2),
                    "median": round(statistics.median(overall_scores), 2),
                    "min": round(min(overall_scores), 2),
                    "max": round(max(overall_scores), 2),
                    "std_dev": round(
                        (
                            statistics.stdev(overall_scores)
                            if len(overall_scores) > 1
                            else 0
                        ),
                        2,
                    ),
                },
                "communication": {
                    "average": round(statistics.mean(communication_scores), 2),
                    "median": round(statistics.median(communication_scores), 2),
                },
                "technical": {
                    "average": round(statistics.mean(technical_scores), 2),
                    "median": round(statistics.median(technical_scores), 2),
                },
                "behavioral": {
                    "average": round(statistics.mean(behavioral_scores), 2),
                    "median": round(statistics.median(behavioral_scores), 2),
                },
            },
            "common_strengths": [
                {"strength": s, "frequency": f} for s, f in top_strengths
            ],
            "common_weaknesses": [
                {"weakness": w, "frequency": f} for w, f in top_weaknesses
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Generated job analytics for '{search_term}'")
        return analytics

    except Exception as e:
        logger.error(f"Error getting job analytics: {e}")
        raise


async def save_user_analytics(user_id: str, analytics_data: Dict[str, Any]) -> str:
    """
    Save user analytics data to Firestore

    Args:
        user_id (str): User ID
        analytics_data (Dict[str, Any]): Analytics data to save

    Returns:
        str: Document ID of saved analytics
    """
    try:
        collection = get_collection(COLLECTIONS["user_analytics"])

        analytics_record = {
            "user_id": user_id,
            "data": analytics_data,
            "generated_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref = await collection.add(analytics_record)

        logger.info(f"User analytics saved for user {user_id}")
        return doc_ref[1].id

    except Exception as e:
        logger.error(f"Error saving user analytics: {e}")
        raise


async def update_user_analytics(user_id: str) -> Dict[str, Any]:
    """
    Update and recalculate user analytics

    Args:
        user_id (str): User ID to update analytics for

    Returns:
        Dict[str, Any]: Updated analytics data
    """
    try:
        # Generate fresh analytics
        analytics_data = await get_analytics_data(user_id)

        # Save to analytics collection
        await save_user_analytics(user_id, analytics_data)

        logger.info(f"Updated analytics for user {user_id}")
        return analytics_data

    except Exception as e:
        logger.error(f"Error updating user analytics: {e}")
        raise


async def get_platform_analytics() -> Dict[str, Any]:
    """
    Get platform-wide analytics

    Returns:
        Dict[str, Any]: Platform analytics data
    """
    try:
        from .interview_sessions import get_all_interview_sessions, count_user_sessions
        from .interview_reports import get_all_interview_reports
        from .user_management import get_user_statistics

        # Get basic statistics
        user_stats = await get_user_statistics()
        sessions = await get_all_interview_sessions(limit=1000)
        reports = await get_all_interview_reports(limit=1000)

        # Calculate platform metrics
        total_sessions = len(sessions)
        completed_sessions = len(
            [s for s in sessions if s.status == InterviewStatus.COMPLETED]
        )
        completion_rate = (
            (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        )

        # Calculate average scores across all reports
        if reports:
            avg_overall_score = sum(r.overall_score for r in reports) / len(reports)
            avg_communication_score = sum(r.communication_score for r in reports) / len(
                reports
            )
            avg_technical_score = sum(r.technical_score for r in reports) / len(reports)
            avg_behavioral_score = sum(r.behavioral_score for r in reports) / len(
                reports
            )
        else:
            avg_overall_score = avg_communication_score = avg_technical_score = (
                avg_behavioral_score
            ) = 0

        # Recent activity (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_sessions = len(
            [s for s in sessions if s.created_at and s.created_at > cutoff_date]
        )
        recent_reports = len(
            [r for r in reports if r.generated_at and r.generated_at > cutoff_date]
        )

        # Most popular job titles and companies
        job_titles = [s.job_title for s in sessions if s.job_title]
        companies = [s.company_name for s in sessions if s.company_name]

        job_title_counts = {}
        company_counts = {}

        for title in job_titles:
            job_title_counts[title] = job_title_counts.get(title, 0) + 1

        for company in companies:
            company_counts[company] = company_counts.get(company, 0) + 1

        top_job_titles = sorted(
            job_title_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_companies = sorted(
            company_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        platform_analytics = {
            "user_statistics": user_stats,
            "interview_statistics": {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "completion_rate": round(completion_rate, 2),
                "total_reports": len(reports),
            },
            "performance_averages": {
                "overall_score": round(avg_overall_score, 2),
                "communication_score": round(avg_communication_score, 2),
                "technical_score": round(avg_technical_score, 2),
                "behavioral_score": round(avg_behavioral_score, 2),
            },
            "recent_activity_30d": {
                "new_sessions": recent_sessions,
                "new_reports": recent_reports,
            },
            "popular_positions": {
                "job_titles": [
                    {"title": title, "count": count} for title, count in top_job_titles
                ],
                "companies": [
                    {"company": company, "count": count}
                    for company, count in top_companies
                ],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info("Generated platform analytics")
        return platform_analytics

    except Exception as e:
        logger.error(f"Error getting platform analytics: {e}")
        raise


async def get_interview_trends(days: int = 90) -> Dict[str, Any]:
    """
    Get interview trends over time

    Args:
        days (int): Number of days to analyze

    Returns:
        Dict[str, Any]: Interview trends data
    """
    try:
        from .interview_sessions import get_all_interview_sessions

        # Get sessions from the specified time period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        sessions = await get_all_interview_sessions(limit=1000)

        # Filter sessions within time period
        filtered_sessions = [
            s for s in sessions if s.created_at and s.created_at > cutoff_date
        ]

        # Group by day
        daily_data = {}
        for session in filtered_sessions:
            day_key = session.created_at.strftime("%Y-%m-%d")

            if day_key not in daily_data:
                daily_data[day_key] = {
                    "total_sessions": 0,
                    "completed_sessions": 0,
                    "in_progress_sessions": 0,
                    "cancelled_sessions": 0,
                }

            daily_data[day_key]["total_sessions"] += 1

            if session.status == InterviewStatus.COMPLETED:
                daily_data[day_key]["completed_sessions"] += 1
            elif session.status == InterviewStatus.IN_PROGRESS:
                daily_data[day_key]["in_progress_sessions"] += 1
            elif session.status == InterviewStatus.CANCELLED:
                daily_data[day_key]["cancelled_sessions"] += 1

        # Convert to sorted list
        trend_data = []
        for day in sorted(daily_data.keys()):
            data = daily_data[day]
            completion_rate = (
                (data["completed_sessions"] / data["total_sessions"] * 100)
                if data["total_sessions"] > 0
                else 0
            )

            trend_data.append(
                {
                    "date": day,
                    "total_sessions": data["total_sessions"],
                    "completed_sessions": data["completed_sessions"],
                    "completion_rate": round(completion_rate, 2),
                    "in_progress": data["in_progress_sessions"],
                    "cancelled": data["cancelled_sessions"],
                }
            )

        trends = {
            "period_days": days,
            "total_days_with_data": len(daily_data),
            "daily_trends": trend_data,
            "summary": {
                "total_sessions": sum(
                    data["total_sessions"] for data in daily_data.values()
                ),
                "average_daily_sessions": (
                    round(
                        sum(data["total_sessions"] for data in daily_data.values())
                        / len(daily_data),
                        2,
                    )
                    if daily_data
                    else 0
                ),
                "peak_day": (
                    max(daily_data.items(), key=lambda x: x[1]["total_sessions"])[0]
                    if daily_data
                    else None
                ),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Generated interview trends for {days} days")
        return trends

    except Exception as e:
        logger.error(f"Error getting interview trends: {e}")
        raise


async def calculate_improvement_score(user_id: str) -> float:
    """
    Calculate improvement score for a user based on their interview history

    Args:
        user_id (str): User ID to calculate improvement for

    Returns:
        float: Improvement score (-100 to +100)
    """
    try:
        from .interview_reports import get_reports_by_user

        reports = await get_reports_by_user(user_id, limit=20)

        if len(reports) < 2:
            return 0.0

        # Sort reports by date
        reports.sort(key=lambda x: x.generated_at)

        # Compare first half vs second half
        mid_point = len(reports) // 2
        first_half = reports[:mid_point]
        second_half = reports[mid_point:]

        first_half_avg = sum(r.overall_score for r in first_half) / len(first_half)
        second_half_avg = sum(r.overall_score for r in second_half) / len(second_half)

        improvement = second_half_avg - first_half_avg

        # Normalize to -100 to +100 scale
        normalized_improvement = max(-100, min(100, improvement))

        return round(normalized_improvement, 2)

    except Exception as e:
        logger.error(f"Error calculating improvement score for user {user_id}: {e}")
        return 0.0
