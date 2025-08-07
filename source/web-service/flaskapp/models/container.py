from flaskapp.models import db
from sqlalchemy.sql import func

# POSTGRESQL - for the upsert mode
from sqlalchemy.dialects.postgresql import insert as pg_insert


class LDPContainer(db.Model):
    __tablename__ = "containers"
    id = db.Column(db.Integer, primary_key=True)
    # Bibliographic metadata elements
    dctitle = db.Column(db.String(150), nullable=False)
    dcdescription = db.Column(db.String, nullable=True)
    datetime_created = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # This is the *relative* subpath for this container, not the FQDN
    # no '/' on the end of the string
    container_identifier = db.Column(
        db.String(200), nullable=False, index=True, unique=True
    )

    # Nullable for root nodes (ie direct members of the LOD Gateway 'container')
    # Model also has a boolean 'is_root' to indicate this (which is better than querying on NULL/None)
    is_root = db.Column(db.Boolean, index=True, default=False)
    parent_id = db.Column(
        db.Integer, db.ForeignKey("containers.id"), index=True, nullable=True
    )

    # Relationship to parent and children. dynamic to avoid SQLAlchemy trying to pull a whole hierarchy
    parent = db.relationship(
        "LDPContainer", remote_side=[id], back_populates="children"
    )
    children = db.relationship("LDPContainer", back_populates="parent", lazy="dynamic")

    # One-to-many relationship with LDPContainerContents
    contents = db.relationship(
        "LDPContainerContents", back_populates="container", lazy="dynamic"
    )

    @classmethod
    def get_root_nodes(cls):
        return (
            cls.query.filter_by(is_root=True)
            .order_by(LDPContainer.datetime_created)
            .all()
        )

    def __repr__(self):
        return f"<LDPContainer id={self.id} path={self.container_identifier} name={self.dctitle}>"

    # Add a child container
    def add_child_container(self, child_container: "LDPContainer", db_dialect="base"):
        child_container.parent = self
        db.session.add(child_container)
        self.add_to_container(child_container, is_container=True)

    # Add a child Record, but do not flush or commit
    def add_to_container(self, item, is_container: bool = False, db_dialect="base"):
        # Get the right details from the item
        if is_container:
            entity_id = item.container_identifier
            entity_type = "ldp:BasicContainer"
        else:
            entity_id = item.entity_id
            entity_type = item.entity_type

        # Probably shift this test to a flag created once when setting up app.config section eventually
        if db_dialect == "postgresql":
            # The index_elements check might be fine with just entity_id actually. Might be slightly quicker.
            stmt = (
                pg_insert(LDPContainerContents)
                .values(
                    container_id=self.id,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    is_container=is_container,
                )
                .on_conflict_do_nothing(constraint="_container_uniqueness_constraint")
            )
            db.session.execute(stmt)
        else:
            # Fallback for non-PostgreSQL databases
            existing = LDPContainerContents.query.filter_by(
                container_id=self.id, entity_id=entity_id
            ).first()
            if not existing:
                new_entity = LDPContainerContents(
                    container_id=self.id,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    is_container=is_container,
                )
                db.session.add(new_entity)

    def paginate_through_content(self, page=1, page_size=100):
        # Paginate through the rows, listing the containers first and then the records,
        # ordered by the
        query = self.contents.order_by(
            db.desc(LDPContainerContents.is_container),  # True first
            LDPContainerContents.id.asc(),
        )

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        pages = (total + page_size - 1) // page_size

        # flatten this to simple classes (str, etc).
        # TODO should the date_added be turned into a string or left for the API to format
        return {
            "items": [x.to_dict() for x in items],
            "total": total,
            "pages": pages,
            "current_page": page,
            "has_next": page < pages,
        }


class LDPContainerContents(db.Model):
    __tablename__ = "entity_list"

    id = db.Column(db.Integer, primary_key=True)
    entity_id = db.Column(db.String(250), nullable=False, unique=True, index=True)
    # NB ldp_BasicLDPContainer will also be present here, for completeness. This should reflect
    entity_type = db.Column(db.String(70), nullable=False)
    # to make child container retrieval and ordering quicker, because it is expected that there will
    # be very many more is_container=False rows than True
    # (NB if it was 50:50 True/False, it won't be optimal and may even slow things down to include this index #theMoreYouKnow)
    is_container = db.Column(db.Boolean, index=True, default=False)
    date_added = db.Column(db.DateTime(timezone=True), server_default=func.now())

    # Has to be part of a LDPContainer
    container_id = db.Column(
        db.Integer, db.ForeignKey("containers.id"), nullable=False, index=True
    )
    container = db.relationship("LDPContainer", back_populates="contents")

    def __repr__(self):
        return f"<LDPContainerContents id={self.id} entity_id={self.entity_id} type={self.entity_type}>"

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "is_container": self.is_container,
            "date_added": self.date_added,
        }
