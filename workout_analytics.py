import pandas as pd
import numpy as np
import json
from datetime import datetime

class WorkoutEfficiencyAnalyzer:
    def __init__(self, user_data=None, workout_data=None):
        self.user_data = user_data
        self.workout_data = workout_data
        self.efficiency_scores = {}
        self.weighted_exercises = ["dl", "fs", "br", "op", "cu", "bp"]
        
    def load_from_json(self, json_data):
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
            
        self.user_data = data.get('user', {})
        self.workout_data = data.get('workouts', [])
        return self
    
    def load_from_df(self, user_df, workout_df):
        self.user_data = user_df.iloc[0].to_dict() if not user_df.empty else {}
        self.workout_data = workout_df.to_dict('records') if not workout_df.empty else []
        return self
        
    def calculate_efficiency_scores(self):
        if not self.workout_data:
            return {}
            
        results = []
        
        for workout in self.workout_data:
            try:
                date = workout.get('date', '')
                calories = float(workout.get('calories_burned', 0))
                duration_min = max(float(workout.get('duration', 0)) / 60, 0.1)
                exercise_data = workout.get('exercise_data', {})
                total_reps = sum(exercise_data.values()) if exercise_data else 0
                intensity = calories / duration_min
                efficiency = calories / max(total_reps, 1)
                density = total_reps / duration_min
                volume_load = self._calculate_volume_load(workout)
                technique_consistency = self._calculate_technique_consistency(workout)
                fatigue_factor = self._calculate_fatigue_factor(workout)
                combined_score = (
                    0.4 * self._normalize(intensity, 0, 15) +  
                    0.3 * self._normalize(efficiency, 0, 0.5) +
                    0.3 * self._normalize(density, 0, 30)
                )
                if technique_consistency is not None:
                    combined_score = 0.8 * combined_score + 0.2 * technique_consistency
                fitness_level = self.user_data.get('fitness_level', 'beginner').lower()
                level_multiplier = {
                    'beginner': 1.2,
                    'intermediate': 1.0,
                    'advanced': 0.9
                }.get(fitness_level, 1.0)
                
                final_score = round(combined_score * level_multiplier * 10, 1)

                category = 'Poor'
                if final_score >= 8:
                    category = 'Excellent'
                elif final_score >= 6:
                    category = 'Good'
                elif final_score >= 4:
                    category = 'Average'
                elif final_score >= 2:
                    category = 'Fair'

                primary_exercise = self._get_primary_exercise(exercise_data)
                is_weighted = primary_exercise in self.weighted_exercises

                result = {
                    'date': date,
                    'raw_metrics': {
                        'calories': calories,
                        'duration_min': duration_min,
                        'total_reps': total_reps,
                    },
                    'efficiency_metrics': {
                        'intensity': round(intensity, 2),
                        'efficiency': round(efficiency, 2),
                        'density': round(density, 2),
                    },
                    'advanced_metrics': {
                        'volume_load': volume_load,
                        'technique_consistency': technique_consistency,
                        'fatigue_factor': fatigue_factor
                    },
                    'score': final_score,
                    'category': category,
                    'primary_exercise': primary_exercise,
                    'is_weighted': is_weighted,
                    'workout_id': workout.get('id', None)
                }
                
                results.append(result)
            except Exception as e:
                print(f"Error processing workout: {e}")
                continue

        self.efficiency_scores = results
        return results
    
    def _calculate_volume_load(self, workout):
        weights_used = workout.get('weights_used', {})
        if not weights_used:
            return None
            
        exercise_data = workout.get('exercise_data', {})
        if not exercise_data:
            return None

        volume_load = 0
        for exercise, reps in exercise_data.items():
            if exercise in self.weighted_exercises and exercise in weights_used:
                weight = weights_used.get(exercise, 0)
                volume_load += weight * reps
                
        return volume_load if volume_load > 0 else None
    
    def _calculate_technique_consistency(self, workout):
        form_issues = workout.get('form_issues_log', [])
        if form_issues is None:
            return None
            
        total_reps = sum(workout.get('exercise_data', {}).values())
        if total_reps == 0:
            return None
            
        if form_issues == []:
            return 1.0
            
        issue_count = len(form_issues)
        consistency = max(0, 1 - (issue_count / total_reps))
        
        return round(consistency, 2)
    
    def _calculate_fatigue_factor(self, workout):
        rep_performance = workout.get('rep_performance', [])
        if not rep_performance or len(rep_performance) < 4:
            return None

        midpoint = len(rep_performance) // 2
        first_half = rep_performance[:midpoint]
        second_half = rep_performance[midpoint:]
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if first_avg <= 0:
            return None
            
        fatigue = max(0, min(1, (first_avg - second_avg) / first_avg))
        
        return round(fatigue, 2)
            
    def get_exercise_efficiency_comparison(self):
        if not self.efficiency_scores:
            self.calculate_efficiency_scores()
            
        exercise_stats = {}
        
        for workout in self.efficiency_scores:
            primary = workout['primary_exercise']
            if primary not in exercise_stats:
                exercise_stats[primary] = {
                    'scores': [],
                    'intensities': [],
                    'efficiencies': [],
                    'densities': [],
                    'is_weighted': workout.get('is_weighted', False),
                    'volume_loads': [],
                    'technique_scores': []
                }
                
            exercise_stats[primary]['scores'].append(workout['score'])
            exercise_stats[primary]['intensities'].append(workout['efficiency_metrics']['intensity'])
            exercise_stats[primary]['efficiencies'].append(workout['efficiency_metrics']['efficiency'])
            exercise_stats[primary]['densities'].append(workout['efficiency_metrics']['density'])
            advanced = workout.get('advanced_metrics', {})
            if advanced.get('volume_load') is not None:
                exercise_stats[primary]['volume_loads'].append(advanced['volume_load'])
            if advanced.get('technique_consistency') is not None:
                exercise_stats[primary]['technique_scores'].append(advanced['technique_consistency'])
        
        comparison = {}
        for exercise, stats in exercise_stats.items():
            comparison_data = {
                'avg_score': round(np.mean(stats['scores']), 1),
                'avg_intensity': round(np.mean(stats['intensities']), 2),
                'avg_efficiency': round(np.mean(stats['efficiencies']), 2),
                'avg_density': round(np.mean(stats['densities']), 2),
                'workout_count': len(stats['scores']),
                'is_weighted': stats['is_weighted']
            }

            if stats['volume_loads']:
                comparison_data['avg_volume_load'] = round(np.mean(stats['volume_loads']), 1)
            if stats['technique_scores']:
                comparison_data['avg_technique'] = round(np.mean(stats['technique_scores']), 2)
            
            comparison[exercise] = comparison_data
            
        return comparison
        
    def get_trend_analysis(self):
        if not self.efficiency_scores:
            self.calculate_efficiency_scores()

        sorted_scores = sorted(self.efficiency_scores, key=lambda x: x['date'])
        
        if len(sorted_scores) < 2:
            return {"trend": "Not enough data", "improvement": 0}

        scores = [workout['score'] for workout in sorted_scores]
        dates = [workout['date'] for workout in sorted_scores]
        first_score = scores[0]
        last_score = scores[-1]        
        improvement = round(((last_score - first_score) / max(first_score, 0.1)) * 100, 1)

        try:
            try:
                first_date = datetime.strptime(dates[0], '%Y-%m-%d')
                days = [(datetime.strptime(date, '%Y-%m-%d') - first_date).days for date in dates]
            except ValueError:
                first_date = datetime.fromisoformat(dates[0].replace('Z', '+00:00'))
                days = [(datetime.fromisoformat(date.replace('Z', '+00:00')) - first_date).days for date in dates]
            
            slope, intercept = np.polyfit(days, scores, 1)
            r_squared = np.corrcoef(days, scores)[0, 1]**2
            volatility = round(np.std(scores), 2)

            if abs(slope) < 0.01:
                trend = "Stable"
            elif slope > 0:
                trend = "Strongly improving" if slope > 0.05 else "Improving"
            else:
                trend = "Strongly declining" if slope < -0.05 else "Declining"
                
            has_plateau = False
            if len(scores) >= 3:
                for i in range(len(scores) - 2):
                    window = scores[i:i+3]
                    if max(window) - min(window) < 0.5:
                        has_plateau = True
        except Exception as e:
            print(f"Error in trend analysis: {e}")
            trend = "Improving" if improvement > 10 else "Declining" if improvement < -10 else "Stable"
            r_squared = None
            volatility = None
            has_plateau = False
            
        return {
            "trend": trend,
            "improvement": improvement,
            "first_score": first_score,
            "last_score": last_score,
            "num_workouts": len(scores),
            "r_squared": round(r_squared, 3) if r_squared is not None else None,
            "volatility": volatility,
            "has_plateau": has_plateau
        }
        
    def get_muscle_group_analysis(self):
        if not self.efficiency_scores:
            self.calculate_efficiency_scores()

        muscle_groups = {
            'Chest': ['bp', 'pu'],
            'Back': ['br', 'dl'],
            'Legs': ['sq', 'fs', 'lu'],
            'Shoulders': ['op'],
            'Arms': ['cu']
        }

        muscle_data = {group: {'count': 0, 'volume': 0, 'efficiency': 0} for group in muscle_groups}
        
        for workout in self.efficiency_scores:
            primary = workout['primary_exercise']
            
            for group, exercises in muscle_groups.items():
                if primary in exercises:
                    muscle_data[group]['count'] += 1
                    muscle_data[group]['efficiency'] += workout['score']
                    
                    if workout.get('advanced_metrics', {}).get('volume_load'):
                        muscle_data[group]['volume'] += workout['advanced_metrics']['volume_load']
                    
        for group in muscle_data:
            if muscle_data[group]['count'] > 0:
                muscle_data[group]['avg_efficiency'] = round(muscle_data[group]['efficiency'] / muscle_data[group]['count'], 1)
            else:
                muscle_data[group]['avg_efficiency'] = 0
                
        return muscle_data
            
    def get_recommendations(self):
        if not self.efficiency_scores:
            self.calculate_efficiency_scores()
            
        recommendations = []
        
        avg_score = np.mean([w['score'] for w in self.efficiency_scores]) if self.efficiency_scores else 0
        if avg_score < 5:
            recommendations.append({
                "type": "tip",
                "title": "Intensity Focus",
                "description": "Focus on maintaining consistent intensity throughout workouts to improve efficiency.",
                "icon": "bx-flame"
            })
        
        trend_data = self.get_trend_analysis()
        if trend_data["trend"] == "Declining" and trend_data["num_workouts"] > 2:
            recommendations.append({
                "type": "warning",
                "title": "Efficiency Decline",
                "description": "Your workout efficiency is declining. Consider varying your routine or increasing intensity.",
                "icon": "bx-trending-down"
            })
        
        if trend_data.get("has_plateau", False):
            recommendations.append({
                "type": "insight",
                "title": "Workout Plateau",
                "description": "You've reached a plateau in workout efficiency. Try changing your variables - increase weight, modify rep ranges, or change exercise order.",
                "icon": "bx-line-chart"
            })
        
        muscle_analysis = self.get_muscle_group_analysis()
        if muscle_analysis:
            workout_counts = [data['count'] for data in muscle_analysis.values()]
            if workout_counts and max(workout_counts) > 0:
                trained_groups = {group: data for group, data in muscle_analysis.items() if data['count'] > 0}
                if trained_groups:
                    least_trained = min(trained_groups.items(), key=lambda x: x[1]['count'])
                    most_trained = max(muscle_analysis.items(), key=lambda x: x[1]['count'])
                    
                    if most_trained[1]['count'] >= 3 * max(1, least_trained[1]['count']):
                        recommendations.append({
                            "type": "insight",
                            "title": "Muscle Balance",
                            "description": f"You're training {most_trained[0]} {most_trained[1]['count']} times more than {least_trained[0]}. Consider balancing your routine for overall development.",
                            "icon": "bx-dumbbell"
                        })
        
        comparison = self.get_exercise_efficiency_comparison()
        if comparison:
            best_exercise = max(comparison.items(), key=lambda x: x[1]['avg_score'])
            worst_exercise = min(comparison.items(), key=lambda x: x[1]['avg_score'])
            
            if best_exercise[0] != worst_exercise[0]:
                recommendations.append({
                    "type": "insight", 
                    "title": "Exercise Comparison",
                    "description": f"Your most efficient exercise is {best_exercise[0]} while {worst_exercise[0]} shows the lowest efficiency. Consider adjusting your approach to {worst_exercise[0]}.",
                    "icon": "bx-dumbbell"
                })
        
        technique_scores = [w.get('advanced_metrics', {}).get('technique_consistency') for w in self.efficiency_scores]
        technique_scores = [score for score in technique_scores if score is not None]
        if technique_scores:
            avg_technique = np.mean(technique_scores)
            if avg_technique < 0.7:
                recommendations.append({
                    "type": "warning",
                    "title": "Form Check",
                    "description": "Your exercise form consistency needs improvement. Focus on proper technique rather than increasing weight or intensity.",
                    "icon": "bx-check-shield"
                })
        
        fatigue_factors = [w.get('advanced_metrics', {}).get('fatigue_factor') for w in self.efficiency_scores]
        fatigue_factors = [f for f in fatigue_factors if f is not None]
        if fatigue_factors:
            avg_fatigue = np.mean(fatigue_factors)
            if avg_fatigue > 0.3:
                recommendations.append({
                    "type": "tip",
                    "title": "Fatigue Management",
                    "description": "Your performance drops significantly during workouts. Consider better warm-ups, improved pacing, or nutrition timing to maintain consistent performance.",
                    "icon": "bx-battery"
                })

        fitness_level = self.user_data.get('fitness_level', 'beginner').lower()
        if fitness_level in ['intermediate', 'advanced']:
            avg_density = np.mean([w['efficiency_metrics'].get('density', 0) for w in self.efficiency_scores]) if self.efficiency_scores else 0
            if avg_density < 8:
                recommendations.append({
                    "type": "tip",
                    "title": "Workout Density",
                    "description": "Try increasing your workout density (reps per minute) by reducing rest periods between sets.",
                    "icon": "bx-time"
                })
        
        return recommendations
        
    def _normalize(self, value, min_val, max_val):
        if value <= min_val:
            return 0
        if value >= max_val:
            return 1
        return (value - min_val) / (max_val - min_val)
        
    def _get_primary_exercise(self, exercise_data):
        if not exercise_data:
            return "unknown"
            
        primary = max(exercise_data.items(), key=lambda x: x[1])
        return primary[0]
        
    def generate_report(self):
        if not self.efficiency_scores:
            self.calculate_efficiency_scores()
            
        trend_analysis = self.get_trend_analysis()
        exercise_comparison = self.get_exercise_efficiency_comparison()
        recommendations = self.get_recommendations()
        muscle_analysis = self.get_muscle_group_analysis()

        consistency_scores = []
        for workout in self.efficiency_scores:
            if workout.get('advanced_metrics', {}).get('technique_consistency') is not None:
                consistency_scores.append(workout['advanced_metrics']['technique_consistency'])
        
        avg_consistency = round(np.mean(consistency_scores), 2) if consistency_scores else None
        
        return {
            "user_info": {
                "name": self.user_data.get("name", ""),
                "fitness_level": self.user_data.get("fitness_level", ""),
                "age": self.user_data.get("age", "")
            },
            "overall_stats": {
                "num_workouts": len(self.efficiency_scores),
                "avg_score": round(np.mean([w['score'] for w in self.efficiency_scores]), 1) if self.efficiency_scores else 0,
                "max_score": round(max([w['score'] for w in self.efficiency_scores]), 1) if self.efficiency_scores else 0,
                "trend": trend_analysis.get("trend", ""),
                "improvement": trend_analysis.get("improvement", 0),
                "r_squared": trend_analysis.get("r_squared"),
                "volatility": trend_analysis.get("volatility"),
                "has_plateau": trend_analysis.get("has_plateau", False),
                "avg_technique_consistency": avg_consistency
            },
            "exercise_comparison": exercise_comparison,
            "muscle_analysis": muscle_analysis,
            "detailed_scores": self.efficiency_scores,
            "recommendations": recommendations
        }