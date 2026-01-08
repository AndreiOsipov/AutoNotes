from db import VideoTranscription, Review, Users
from sqlmodel import Session, select, join, desc, asc

class ReviewCRUD:
    
    @staticmethod
    def get_user_by_username(session: Session, username: str) -> Optional[Users]:
        return session.exec(
            select(Users).where(Users.username == username)
        ).first()

    @staticmethod
    def create_review(session: Session, review_data: dict) -> Review:
        username = review_data.get('username')
        if not username:
            raise ValueError("Incorrect username")
        user = ReviewCRUD.get_user_by_username(session, username)
        if not user:
            raise ValueError(f"User {username} not found")
        transcription_id = review_data.get('transcription_id')
        if transcription_id is not None:
            transcription = session.get(VideoTranscription, transcription_id)
            if not transcription:
                raise ValueError(f"transcription_id not found")
        rating = review_data.get('rating')
        if rating is not None and not (1 <= rating <= 5):
            raise ValueError("The rating should be from 1 to 5")
        comment = review_data.get('comment', '')
        if len(comment) > 2000:
            raise ValueError("The review must not exceed 2000 characters.")
        review = Review(
            user_id=user.id,
            transcription_id=transcription_id,
            rating=rating,
            comment=comment
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
    
    def get_service_reviews(
        session: Session,
        limit: int = 10,
        sort_by: str = "newest"
    ) -> List[Review]:
        if limit < 1 or limit > 100:
            raise ValueError("The limit should be from 1 to 100")
        if sort_by not in ["newest", "oldest", "best", "worst"]:
            raise ValueError("Incorrect sorting parameter")        
        statement = (
            select(
                Review.id,
                Users.username,
                Review.transcription_id,
                Review.rating,
                Review.comment,
                Review.created_dt_tm
            )
            .select_from(join(Review, Users, Review.user_id == Users.id))
            .where(Review.transcription_id.is_(None))
        )
        if sort_by == "newest":
            statement = statement.order_by(desc(Review.created_dt_tm))
        elif sort_by == "oldest":
            statement = statement.order_by(asc(Review.created_dt_tm))
        elif sort_by == "best":
            statement = statement.order_by(
                desc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        elif sort_by == "worst":
            statement = statement.order_by(
                asc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        
        statement = statement.limit(limit)
        return session.exec(statement).all()
    
    @staticmethod
    def get_transcription_reviews(
        session: Session,
        transcription_id: int,
        limit: int = 10,
        sort_by: str = "newest"
    ) -> List[Review]:
        if limit < 1 or limit > 100:
            raise ValueError("The limit should be from 1 to 100")
        if sort_by not in ["newest", "oldest", "best", "worst"]:
            raise ValueError("Incorrect sorting parameter")
        
        transcription = session.get(VideoTranscription, transcription_id)
        if not transcription:
            raise ValueError(f"transcription_id not found")
        
        statement = (
            select(
                Review.id,
                Users.username,
                Review.transcription_id,
                Review.rating,
                Review.comment,
                Review.created_dt_tm
            )
            .select_from(join(Review, Users, Review.user_id == Users.id))
            .where(Review.transcription_id == transcription_id)
        )
        
        if sort_by == "newest":
            statement = statement.order_by(desc(Review.created_dt_tm))
        elif sort_by == "oldest":
            statement = statement.order_by(asc(Review.created_dt_tm))
        elif sort_by == "best":
            statement = statement.order_by(
                desc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        elif sort_by == "worst":
            statement = statement.order_by(
                asc(Review.rating), 
                desc(Review.created_dt_tm)
            )
        
        statement = statement.limit(limit)
        return session.exec(statement).all()
